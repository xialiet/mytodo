from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from pathlib import Path
from fastapi.responses import HTMLResponse
import os
import jinja2

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATA_DIR, 'mytodo.db')}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

templates_path = Path(__file__).parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(templates_path)),
    autoescape=True,
)


class templates:
    @staticmethod
    def TemplateResponse(name, context):
        tmpl = _jinja_env.get_template(name)
        html = tmpl.render(**context)
        return HTMLResponse(html)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 幂等迁移：为已有数据库添加循环任务字段
        for col, coltype in [
            ("recurrence_type", "VARCHAR(20)"),
            ("recurrence_interval", "INTEGER"),
            ("recurrence_copy_subtasks", "BOOLEAN"),
            ("start_date", "DATE"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE todos ADD COLUMN {col} {coltype}"))
            except Exception:
                pass  # 列已存在，跳过
        # 打卡表的 denormalized date 列（Base.metadata.create_all 已建过表，但旧库可能缺）
        try:
            await conn.execute(text("ALTER TABLE checkin_logs ADD COLUMN date DATE"))
        except Exception:
            pass
        try:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_checkin_logs_item_date ON checkin_logs(item_id, date)"))
        except Exception:
            pass
