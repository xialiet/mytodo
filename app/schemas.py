from pydantic import BaseModel, Field
from typing import Optional


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#6b7280", pattern=r"^#[0-9a-fA-F]{6}$")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    category_id: Optional[int] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    priority: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    recurrence_type: Optional[str] = Field(default=None, pattern=r"^(daily|weekly|biweekly|monthly|custom)$")
    recurrence_interval: Optional[int] = Field(default=None, ge=1)
    recurrence_copy_subtasks: bool = False


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    priority: Optional[str] = Field(default=None, pattern=r"^(low|medium|high)$")
    status: Optional[str] = Field(default=None, pattern=r"^(pending|done)$")
    recurrence_type: Optional[str] = Field(default=None, pattern=r"^(daily|weekly|biweekly|monthly|custom)$")
    recurrence_interval: Optional[int] = Field(default=None, ge=1)
    recurrence_copy_subtasks: Optional[bool] = None


class SubTaskCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


class SubTaskUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=200)
    done: Optional[bool] = None
    order: Optional[int] = None


class CheckinItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    category_id: Optional[int] = None
    icon: str = Field(default="✅", max_length=8)
    color: str = Field(default="#10b981", pattern=r"^#[0-9a-fA-F]{6}$")
    target_per_day: int = Field(default=1, ge=0)  # 0 = 不限


class CheckinItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    icon: Optional[str] = Field(default=None, max_length=8)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    target_per_day: Optional[int] = Field(default=None, ge=0)
    sort_order: Optional[int] = None
    is_archived: Optional[bool] = None


class CheckinLogCreate(BaseModel):
    note: str = Field(default="", max_length=200)
