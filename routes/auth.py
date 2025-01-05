from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import secrets
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# 从环境变量或配置文件获取
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not secrets.compare_digest(username, ADMIN_USERNAME) or \
       not secrets.compare_digest(password, ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    request.session["authenticated"] = True
    request.session["username"] = username
    request.session["is_admin"] = True
    request.session["user"] = {"username": username, "is_admin": True}
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
