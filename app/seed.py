from sqlalchemy import select, func
from datetime import date, datetime, timezone

from app.database import async_session
from app.models import Category, Todo, SubTask

SEED_CATEGORIES = [
    {"name": "工作", "color": "#2563eb"},
    {"name": "生活", "color": "#16a34a"},
    {"name": "学习", "color": "#9333ea"},
    {"name": "健康", "color": "#dc2626"},
]

SEED_TODOS = [
    {"title": "欢迎使用 MyTodo！这是一个示例待办，可以随意编辑或删除", "priority": "medium", "due_date": None},
    {"title": "完成本周项目周报", "priority": "high", "due_date": None},
    {"title": "整理读书笔记", "priority": "low", "due_date": None},
    {"title": "预约下周体检", "priority": "medium", "due_date": None},
]


SEED_SUBTASKS = [
    {
        "match": "示例待办",
        "items": [
            "点击待办可展开/折叠子任务",
            "左侧勾选完成，右侧可拖拽排序",
            "试试在「打卡」页添加一个每日打卡项",
        ],
    },
]


async def seed_initial_data():
    async with async_session() as db:
        await _seed_categories(db)
        await _seed_todos(db)
        await _seed_subtasks(db)


async def _seed_categories(db):
    result = await db.execute(select(func.count(Category.id)))
    if (result.scalar() or 0) > 0:
        return
    for cat_data in SEED_CATEGORIES:
        db.add(Category(**cat_data))
    await db.commit()


async def _seed_todos(db):
    result = await db.execute(select(func.count(Todo.id)))
    if (result.scalar() or 0) > 0:
        return
    ops_result = await db.execute(select(Category).where(Category.name == "工作"))
    ops_category = ops_result.scalar_one()
    for todo_data in SEED_TODOS:
        db.add(
            Todo(
                title=todo_data["title"],
                priority=todo_data["priority"],
                due_date=todo_data["due_date"],
                category_id=ops_category.id,
                status="pending",
            )
        )
    await db.commit()


async def _seed_subtasks(db):
    result = await db.execute(select(func.count(SubTask.id)))
    if (result.scalar() or 0) > 0:
        return
    for entry in SEED_SUBTASKS:
        todo_result = await db.execute(
            select(Todo).where(Todo.title.contains(entry["match"]))
        )
        todo = todo_result.scalar_one_or_none()
        if not todo:
            continue
        for i, text in enumerate(entry["items"]):
            db.add(SubTask(todo_id=todo.id, text=text, done=False, order=i))
    await db.commit()
