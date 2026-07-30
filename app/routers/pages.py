from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, templates
from app.models import Category

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def page_index(request: Request, db: AsyncSession = Depends(get_db)):
    cat_result = await db.execute(select(Category).order_by(Category.id))
    categories = cat_result.scalars().all()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "categories": categories, "active_tab": "todos"},
    )


@router.get("/categories", response_class=HTMLResponse)
async def page_categories(request: Request):
    return templates.TemplateResponse(
        "categories.html", {"request": request, "active_tab": "categories"}
    )


@router.get("/timeline", response_class=HTMLResponse)
async def page_timeline(request: Request, db: AsyncSession = Depends(get_db)):
    cat_result = await db.execute(select(Category).order_by(Category.id))
    categories = cat_result.scalars().all()
    return templates.TemplateResponse(
        "timeline.html",
        {"request": request, "categories": categories, "active_tab": "timeline"},
    )


@router.get("/stats", response_class=HTMLResponse)
async def page_stats(request: Request, db: AsyncSession = Depends(get_db)):
    cat_result = await db.execute(select(Category).order_by(Category.id))
    categories = cat_result.scalars().all()
    return templates.TemplateResponse(
        "stats.html",
        {"request": request, "categories": categories, "active_tab": "stats"},
    )


@router.get("/checkin", response_class=HTMLResponse)
async def page_checkin(request: Request, db: AsyncSession = Depends(get_db)):
    cat_result = await db.execute(select(Category).order_by(Category.id))
    categories = cat_result.scalars().all()
    return templates.TemplateResponse(
        "checkin.html",
        {"request": request, "categories": categories, "active_tab": "checkin"},
    )

@router.get("/search", response_class=HTMLResponse)
async def page_search(request: Request, db: AsyncSession = Depends(get_db)):
    cat_result = await db.execute(select(Category).order_by(Category.id))
    categories = cat_result.scalars().all()
    return templates.TemplateResponse(
        "search.html",
        {"request": request, "categories": categories, "active_tab": "search"},
    )
