from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone, date, timedelta

from app.database import get_db
from app.models import Category, Todo, SubTask, CheckinItem, CheckinLog
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    TodoCreate,
    TodoUpdate,
    SubTaskCreate,
    SubTaskUpdate,
    CheckinItemCreate,
    CheckinItemUpdate,
    CheckinLogCreate,
)

router = APIRouter()

# 统一本地时区：打卡的写入与查询必须用同一个日期口径，否则凌晨打卡会落到"昨天"
CST = timezone(timedelta(hours=8))


def _utc_iso(dt):
    """SQLite 的 DateTime 列是 naive 的（存的时候丢了 tzinfo），但语义上是 UTC。
    序列化时补上 UTC 标注，前端 new Date() 才能正确按 UTC 解析、转本地时区显示。"""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _serialize_todo(t: Todo, cat_name, cat_color, subtask_total=None, subtask_done=None) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description or "",
        "category_id": t.category_id,
        "category_name": cat_name,
        "category_color": cat_color,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "priority": t.priority,
        "status": t.status,
        "created_at": _utc_iso(t.created_at),
        "completed_at": _utc_iso(t.completed_at),
        "recurrence_type": t.recurrence_type,
        "recurrence_interval": t.recurrence_interval,
        "recurrence_copy_subtasks": t.recurrence_copy_subtasks or False,
        "subtask_total": subtask_total if subtask_total is not None else 0,
        "subtask_done": subtask_done if subtask_done is not None else 0,
    }


def _parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"日期格式错误：{s}，应为 YYYY-MM-DD")


def _calc_next_due(current_due: date, recurrence_type: str, interval: int | None) -> date:
    """计算循环任务下次截止日期"""
    if recurrence_type == "daily":
        return current_due + timedelta(days=1)
    elif recurrence_type == "weekly":
        return current_due + timedelta(weeks=1)
    elif recurrence_type == "biweekly":
        return current_due + timedelta(weeks=2)
    elif recurrence_type == "monthly":
        # 手动月+1，clamp 到月末
        y, m = current_due.year, current_due.month
        m += 1
        if m > 12:
            m = 1
            y += 1
        days_in_month = [31, 28 + (1 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 0),
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        day = min(current_due.day, days_in_month[m - 1])
        return current_due.replace(year=y, month=m, day=day)
    elif recurrence_type == "custom":
        return current_due + timedelta(days=(interval or 1))
    else:
        return current_due + timedelta(days=1)


@router.get("/api/todos")
async def api_list_todos(
    status: str | None = Query(default=None, pattern=r"^(pending|done)$"),
    category_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    overdue: bool = Query(default=False),
    limit: int | None = Query(default=None, ge=1, le=500, description="最多返回条数；默认不限"),
    db: AsyncSession = Depends(get_db),
):
    # 子任务进度（标量子查询，避免 N+1）
    sub_total = (
        select(func.count(SubTask.id))
        .where(SubTask.todo_id == Todo.id)
        .correlate(Todo)
        .scalar_subquery()
        .label("subtask_total")
    )
    sub_done = (
        select(func.count(SubTask.id))
        .where(SubTask.todo_id == Todo.id, SubTask.done.is_(True))
        .correlate(Todo)
        .scalar_subquery()
        .label("subtask_done")
    )

    stmt = (
        select(Todo, Category.name, Category.color, sub_total, sub_done)
        .outerjoin(Category, Todo.category_id == Category.id)
    )

    conditions = []
    if status:
        conditions.append(Todo.status == status)
    if category_id:
        conditions.append(Todo.category_id == category_id)
    if q:
        conditions.append(Todo.title.contains(q))
    if overdue:
        today = datetime.now(CST).date()
        conditions.append(
            and_(Todo.status == "pending", Todo.due_date.isnot(None), Todo.due_date < today)
        )
    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(
        Todo.status.asc(),
        Todo.priority.desc(),
        Todo.due_date.is_(None).asc(),
        Todo.due_date.asc(),
        Todo.created_at.desc(),
    )
    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.all()
    return [_serialize_todo(t, name, color, st or 0, sd or 0) for t, name, color, st, sd in rows]


@router.post("/api/todos")
async def api_create_todo(data: TodoCreate, db: AsyncSession = Depends(get_db)):
    todo = Todo(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        due_date=_parse_date(data.due_date),
        start_date=_parse_date(data.start_date),
        priority=data.priority,
        recurrence_type=data.recurrence_type,
        recurrence_interval=data.recurrence_interval,
        recurrence_copy_subtasks=data.recurrence_copy_subtasks,
    )
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return {"id": todo.id}


@router.patch("/api/todos/{todo_id}")
async def api_update_todo(
    todo_id: int, data: TodoUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")

    updates = data.model_dump(exclude_unset=True)
    if "due_date" in updates:
        updates["due_date"] = _parse_date(updates["due_date"]) if updates["due_date"] is not None else None
    if "start_date" in updates:
        updates["start_date"] = _parse_date(updates["start_date"]) if updates["start_date"] is not None else None
    if updates.get("status") == "done":
        updates["completed_at"] = datetime.now(timezone.utc)
    elif updates.get("status") == "pending":
        updates["completed_at"] = None

    for k, v in updates.items():
        setattr(todo, k, v)
    todo.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.delete("/api/todos/{todo_id}")
async def api_delete_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    await db.delete(todo)
    await db.commit()
    return {"ok": True}


@router.post("/api/todos/{todo_id}/complete")
async def api_complete_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")

    # 标记当前待办为完成
    todo.status = "done"
    todo.completed_at = datetime.now(timezone.utc)
    todo.updated_at = datetime.now(timezone.utc)

    new_todo_id = None

    # 如果是循环任务，自动生成下一次待办
    if todo.recurrence_type:
        base_date = todo.due_date or datetime.now(CST).date()
        next_due = _calc_next_due(base_date, todo.recurrence_type, todo.recurrence_interval)
        # 漏做补卡：若算出的下次 due 仍在今天或更早（漏做了若干天），
        # 则向前推周期直到落在未来，避免下次一上来就过期。
        today = datetime.now(CST).date()
        # 单周期天数，用于推进
        if todo.recurrence_type == "daily":
            step = timedelta(days=1)
        elif todo.recurrence_type == "weekly":
            step = timedelta(weeks=1)
        elif todo.recurrence_type == "biweekly":
            step = timedelta(weeks=2)
        elif todo.recurrence_type == "custom":
            step = timedelta(days=todo.recurrence_interval or 1)
        else:  # monthly：用一个粗略的月步进
            step = timedelta(days=30)
        guard = 0
        while next_due <= today and guard < 400:  # 防止极端情况下死循环
            next_due = next_due + step
            guard += 1

        next_todo = Todo(
            title=todo.title,
            description=todo.description,
            category_id=todo.category_id,
            due_date=next_due,
            priority=todo.priority,
            status="pending",
            recurrence_type=todo.recurrence_type,
            recurrence_interval=todo.recurrence_interval,
            recurrence_copy_subtasks=todo.recurrence_copy_subtasks,
        )
        db.add(next_todo)
        await db.flush()  # 获取新 ID，但不提交

        new_todo_id = next_todo.id

        # 如果配置了复制子任务，复制当前待办的子任务（重置为未完成）
        if todo.recurrence_copy_subtasks and todo.subtasks:
            for i, sub in enumerate(todo.subtasks):
                db.add(SubTask(
                    todo_id=next_todo.id,
                    text=sub.text,
                    done=False,
                    order=i,
                ))

    await db.commit()

    response = {"ok": True}
    if new_todo_id:
        response["next_todo_id"] = new_todo_id
    return response


@router.post("/api/todos/{todo_id}/reopen")
async def api_reopen_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if not todo:
        raise HTTPException(status_code=404, detail="待办不存在")
    todo.status = "pending"
    todo.completed_at = None
    todo.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


@router.get("/api/todos/{todo_id}")
async def api_get_todo(todo_id: int, db: AsyncSession = Depends(get_db)):
    sub_total = (
        select(func.count(SubTask.id))
        .where(SubTask.todo_id == Todo.id)
        .correlate(Todo)
        .scalar_subquery()
    )
    sub_done = (
        select(func.count(SubTask.id))
        .where(SubTask.todo_id == Todo.id, SubTask.done.is_(True))
        .correlate(Todo)
        .scalar_subquery()
    )
    stmt = (
        select(Todo, Category.name, Category.color, sub_total, sub_done)
        .outerjoin(Category, Todo.category_id == Category.id)
        .where(Todo.id == todo_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="待办不存在")
    t, name, color, st, sd = row
    return _serialize_todo(t, name, color, st or 0, sd or 0)


@router.get("/api/todos/{todo_id}/subtasks")
async def api_list_subtasks(todo_id: int, db: AsyncSession = Depends(get_db)):
    todo_result = await db.execute(select(Todo).where(Todo.id == todo_id))
    if not todo_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="待办不存在")
    result = await db.execute(
        select(SubTask)
        .where(SubTask.todo_id == todo_id)
        .order_by(SubTask.order, SubTask.id)
    )
    subs = result.scalars().all()
    return [
        {"id": s.id, "text": s.text, "done": s.done, "order": s.order}
        for s in subs
    ]


@router.post("/api/todos/{todo_id}/subtasks")
async def api_create_subtask(
    todo_id: int, data: SubTaskCreate, db: AsyncSession = Depends(get_db)
):
    todo_result = await db.execute(select(Todo).where(Todo.id == todo_id))
    if not todo_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="待办不存在")
    max_order_result = await db.execute(
        select(func.max(SubTask.order)).where(SubTask.todo_id == todo_id)
    )
    max_order = max_order_result.scalar() or 0
    sub = SubTask(todo_id=todo_id, text=data.text, done=False, order=max_order + 1)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"id": sub.id}


@router.patch("/api/subtasks/{subtask_id}")
async def api_update_subtask(
    subtask_id: int, data: SubTaskUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SubTask).where(SubTask.id == subtask_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="子任务不存在")
    updates = data.model_dump(exclude_none=True)
    for k, v in updates.items():
        setattr(sub, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/api/subtasks/{subtask_id}")
async def api_delete_subtask(subtask_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SubTask).where(SubTask.id == subtask_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="子任务不存在")
    await db.delete(sub)
    await db.commit()
    return {"ok": True}


@router.get("/api/categories")
async def api_list_categories(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            Category.id,
            Category.name,
            Category.color,
            func.count(Todo.id).label("todo_count"),
        )
        .outerjoin(Todo, Todo.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {"id": r.id, "name": r.name, "color": r.color, "todo_count": r.todo_count}
        for r in rows
    ]


@router.post("/api/categories")
async def api_create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Category).where(Category.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类名已存在")
    cat = Category(name=data.name, color=data.color)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": cat.id}


@router.patch("/api/categories/{category_id}")
async def api_update_category(
    category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    updates = data.model_dump(exclude_none=True)
    if "name" in updates and updates["name"] != cat.name:
        existing = await db.execute(
            select(Category).where(Category.name == updates["name"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="分类名已存在")

    for k, v in updates.items():
        setattr(cat, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/api/categories/{category_id}")
async def api_delete_category(
    category_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")

    count_result = await db.execute(
        select(func.count(Todo.id)).where(Todo.category_id == category_id)
    )
    count = count_result.scalar() or 0
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"分类下还有 {count} 个待办，无法删除",
        )

    await db.delete(cat)
    await db.commit()
    return {"ok": True}


# ========== 打卡功能 ==========

def _serialize_checkin_item(it, cat_name, cat_color, today_count, today_logs):
    return {
        "id": it.id,
        "title": it.title,
        "description": it.description or "",
        "category_id": it.category_id,
        "category_name": cat_name,
        "category_color": cat_color,
        "icon": it.icon or "✅",
        "color": it.color or "#10b981",
        "target_per_day": it.target_per_day,
        "is_archived": it.is_archived,
        "sort_order": it.sort_order,
        "today_count": today_count,
        "today_logs": today_logs,
        "created_at": it.created_at.isoformat() if it.created_at else None,
    }


@router.get("/api/checkin/items")
async def list_checkin_items(
    include_archived: bool = Query(default=False),
    date_str: str | None = Query(default=None, description="YYYY-MM-DD；默认今天"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CheckinItem, Category.name, Category.color).outerjoin(
        Category, CheckinItem.category_id == Category.id
    )
    if not include_archived:
        stmt = stmt.where(CheckinItem.is_archived == False)
    stmt = stmt.order_by(CheckinItem.sort_order, CheckinItem.id)
    rows = (await db.execute(stmt)).all()

    target_day = date.fromisoformat(date_str) if date_str else datetime.now(CST).date()
    item_ids = [it.id for it, _, _ in rows]

    # 一次性查每个 item 当日的次数（替代逐条 N+1 查询）
    count_map: dict[int, int] = defaultdict(int)
    logs_map: dict[int, list] = defaultdict(list)
    if item_ids:
        count_rows = (await db.execute(
            select(CheckinLog.item_id, func.count(CheckinLog.id))
            .where(CheckinLog.item_id.in_(item_ids), CheckinLog.date == target_day)
            .group_by(CheckinLog.item_id)
        )).all()
        for iid, cnt in count_rows:
            count_map[iid] = cnt

        # 最近 5 次：用 ROW_NUMBER() 窗口函数一次取回每个 item 的 top-5，避免 N 次 limit 查询
        rn = (
            func.row_number()
            .over(
                partition_by=CheckinLog.item_id,
                order_by=CheckinLog.checked_at.desc(),
            )
            .label("rn")
        )
        log_rows = (await db.execute(
            select(CheckinLog.id, CheckinLog.item_id, CheckinLog.checked_at, rn)
            .where(CheckinLog.item_id.in_(item_ids), CheckinLog.date == target_day)
        )).all()
        for lid, iid, checked_at, r in log_rows:
            if r <= 5:
                logs_map[iid].append({
                    "id": lid,
                    "checked_at": checked_at.isoformat() if checked_at else None,
                })

    items = []
    for it, cat_name, cat_color in rows:
        today_logs = list(reversed(logs_map.get(it.id, [])))  # 最近 5 条，按时间倒序展示
        items.append(_serialize_checkin_item(it, cat_name, cat_color, count_map.get(it.id, 0), today_logs))
    return items


@router.post("/api/checkin/items")
async def create_checkin_item(data: CheckinItemCreate, db: AsyncSession = Depends(get_db)):
    it = CheckinItem(**data.model_dump())
    db.add(it)
    await db.commit()
    await db.refresh(it)
    return {"id": it.id}


@router.patch("/api/checkin/items/{item_id}")
async def update_checkin_item(item_id: int, data: CheckinItemUpdate, db: AsyncSession = Depends(get_db)):
    it = (await db.execute(select(CheckinItem).where(CheckinItem.id == item_id))).scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="打卡项不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(it, k, v)
    await db.commit()
    return {"ok": True}


@router.delete("/api/checkin/items/{item_id}")
async def delete_checkin_item(item_id: int, db: AsyncSession = Depends(get_db)):
    it = (await db.execute(select(CheckinItem).where(CheckinItem.id == item_id))).scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="打卡项不存在")
    await db.delete(it)
    await db.commit()
    return {"ok": True}


@router.post("/api/checkin/items/{item_id}/log")
async def log_checkin(
    item_id: int,
    data: CheckinLogCreate = Body(default_factory=CheckinLogCreate),
    db: AsyncSession = Depends(get_db),
):
    it = (await db.execute(select(CheckinItem).where(CheckinItem.id == item_id))).scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="打卡项不存在")
    now = datetime.now(CST)  # 本地时间，与查询口径一致
    log = CheckinLog(item_id=item_id, checked_at=now, date=now.date(), note=data.note)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return {"id": log.id, "checked_at": log.checked_at.isoformat()}


@router.delete("/api/checkin/logs/{log_id}")
async def delete_checkin_log(log_id: int, db: AsyncSession = Depends(get_db)):
    log = (await db.execute(select(CheckinLog).where(CheckinLog.id == log_id))).scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="记录不存在")
    await db.delete(log)
    await db.commit()
    return {"ok": True}


@router.get("/api/checkin/logs/batch")
async def logs_batch(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """批量返回所有打卡项近 N 天每天的次数。一次请求替代前端逐项 N 次，
    结构 {item_id: [{date, count}, ...]}，日期升序。"""
    today = datetime.now(CST).date()
    start = today - timedelta(days=days - 1)
    rows = (await db.execute(
        select(CheckinLog.item_id, CheckinLog.date, func.count(CheckinLog.id))
        .where(CheckinLog.date >= start)
        .group_by(CheckinLog.item_id, CheckinLog.date)
    )).all()
    by_item_day: dict[int, dict[str, int]] = defaultdict(dict)
    for iid, d, c in rows:
        by_item_day[iid][d.isoformat()] = c
    full = [
        (start + timedelta(days=i)).isoformat()
        for i in range(days)
    ]
    return {
        str(iid): [{"date": ds, "count": by_item_day[iid].get(ds, 0)} for ds in full]
        for iid in by_item_day
    }


@router.get("/api/checkin/items/{item_id}/logs")
async def item_logs(
    item_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """返回近 N 天每天的次数（按日期升序），用于日历热力图和连续天数计算。"""
    today = datetime.now(CST).date()
    start = today - timedelta(days=days - 1)
    rows = (await db.execute(
        select(CheckinLog.date, func.count(CheckinLog.id))
        .where(CheckinLog.item_id == item_id, CheckinLog.date >= start)
        .group_by(CheckinLog.date)
        .order_by(CheckinLog.date)
    )).all()
    by_day = {d.isoformat(): c for d, c in rows}
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "count": by_day.get((start + timedelta(days=i)).isoformat(), 0)}
        for i in range(days)
    ]
