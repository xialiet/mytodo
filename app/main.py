from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routers import pages, api
from app.seed import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_initial_data()
    yield


app = FastAPI(title="MyTodo", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def sw_scope_header(request: Request, call_next):
    """给 /static/sw.js 加 Service-Worker-Allowed: / 头，
    允许 SW 控制整个站点（默认 SW 只能控制自身所在路径 /static/）。"""
    response = await call_next(request)
    if request.url.path == "/static/sw.js":
        response.headers["Service-Worker-Allowed"] = "/"
    return response


app.include_router(pages.router)
app.include_router(api.router)
