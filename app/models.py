from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    color = Column(String(7), default="#6b7280")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    todos = relationship("Todo", back_populates="category")


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)  # 开始日期，None=不限开始日（兼容旧数据）
    priority = Column(String(10), default="medium")
    status = Column(String(10), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime, nullable=True)

    # 循环任务字段
    recurrence_type = Column(String(20), nullable=True)      # daily/weekly/biweekly/monthly/custom, None=不重复
    recurrence_interval = Column(Integer, nullable=True)     # 仅 custom 时用，天数
    recurrence_copy_subtasks = Column(Boolean, nullable=True)  # 是否复制子任务

    category = relationship("Category", back_populates="todos")
    subtasks = relationship(
        "SubTask",
        back_populates="todo",
        cascade="all, delete-orphan",
        order_by="SubTask.order",
    )


class SubTask(Base):
    __tablename__ = "subtasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    todo_id = Column(Integer, ForeignKey("todos.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(200), nullable=False)
    done = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    todo = relationship("Todo", back_populates="subtasks")


class CheckinItem(Base):
    __tablename__ = "checkin_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    icon = Column(String(8), default="✅")
    color = Column(String(7), default="#10b981")
    target_per_day = Column(Integer, default=1)  # 0 = 不限
    is_archived = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    category = relationship("Category")
    logs = relationship(
        "CheckinLog",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="CheckinLog.checked_at.desc()",
    )


class CheckinLog(Base):
    __tablename__ = "checkin_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("checkin_items.id", ondelete="CASCADE"), nullable=False)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    date = Column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False)
    note = Column(String(200), default="")

    item = relationship("CheckinItem", back_populates="logs")

    __table_args__ = (
        Index("ix_checkin_logs_item_date", "item_id", "date"),
    )
