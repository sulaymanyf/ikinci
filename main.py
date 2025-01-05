import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from routes import items, auth, api, admin
from utils.template_filters import format_datetime

app = FastAPI()

# 配置中间件
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secret-key",
    session_cookie="session"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置模板
templates = Jinja2Templates(directory="templates")
templates.env.filters["format_datetime"] = format_datetime

# 注册路由
app.include_router(items.router)
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(admin.router)
