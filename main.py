from fastapi import FastAPI, Request, Depends, HTTPException, Form, Response, File, UploadFile, Query, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
import models
from database import engine, get_db, SessionLocal
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Optional
from utils.image_uploader import ImageUploader
from utils.markdown_importer import MarkdownImporter
from utils.database_exporter import DatabaseExporter
from utils.visit_tracker import visit_tracker
from pathlib import Path
import datetime
from sqlalchemy import func, and_

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 配置静态文件
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# 配置模板
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 获取当前用户
async def get_current_user(request: Request):
    user = request.session.get("user")
    return user

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await visit_tracker.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await visit_tracker.disconnect(websocket)

@app.get("/")
async def read_root(
    request: Request,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # 更新访问统计
    total_visits = visit_tracker.increment_total_visits()
    visit_tracker.increment_page_view('home')
    
    user = await get_current_user(request)
    
    # 获取所有分类及其商品数量（包括已售出的）
    categories_with_count = db.query(
        models.Category,
        func.count(models.Item.id).label('item_count')
    ).outerjoin(
        models.Item,
        models.Category.id == models.Item.category_id
    ).group_by(models.Category.id).all()
    
    # 构建基础查询
    base_query = db.query(models.Item)
    
    # 如果指定了分类，添加分类过滤
    if category_id:
        base_query = base_query.filter(models.Item.category_id == category_id)
    
    # 分别获取未售出和已售出的商品
    unsold_items = base_query.filter(models.Item.is_sold == False).order_by(models.Item.id.desc()).all()
    sold_items = base_query.filter(models.Item.is_sold == True).order_by(models.Item.id.desc()).all()
    
    # 合并商品列表，未售出的在前，已售出的在后
    items = unsold_items + sold_items
    
    # 获取每个商品的第一张图片
    for item in items:
        item.first_image = db.query(models.ItemImage).filter(
            models.ItemImage.item_id == item.id
        ).first()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "items": items,
            "user": user,
            "categories": categories_with_count,
            "current_category": category_id,
            "total_visits": total_visits,
            "page_views": visit_tracker.get_page_views('home')
        }
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    # 这里使用硬编码的管理员账号，实际应用中应该从数据库验证
    if username == "yeaile" and password == "yeaile!@":
        request.session["user"] = {"username": username, "is_admin": True}
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
        status_code=400
    )

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/item/{item_id}")
async def item_detail(request: Request, item_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse("item_detail.html", {"request": request, "item": item, "user": user})

# 管理员路由
@app.get("/admin")
async def admin_panel(request: Request):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})

# 分类管理路由
@app.get("/categories")
async def categories(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("categories.html", {
        "request": request,
        "categories": categories,
        "user": user,
        "edit_category": None
    })

@app.get("/categories/{category_id}")
async def edit_category(request: Request, category_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("categories.html", {
        "request": request,
        "categories": categories,
        "user": user,
        "edit_category": category
    })

@app.post("/categories")
async def add_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 检查分类名是否已存在
    existing = db.query(models.Category).filter(models.Category.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")
    
    category = models.Category(name=name, description=description)
    db.add(category)
    db.commit()
    
    return RedirectResponse(url="/categories", status_code=303)

@app.post("/categories/{category_id}")
async def update_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 检查新名称是否与其他分类重复
    existing = db.query(models.Category).filter(
        models.Category.name == name,
        models.Category.id != category_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists")
    
    category.name = name
    category.description = description
    db.commit()
    
    return RedirectResponse(url="/categories", status_code=303)

@app.delete("/categories/{category_id}")
async def delete_category(request: Request, category_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 检查是否有商品使用此分类
    if len(category.items) > 0:
        raise HTTPException(status_code=400, detail="Cannot delete category with items")
    
    db.delete(category)
    db.commit()
    
    return Response(status_code=200)

@app.get("/add-item")
async def add_item_page(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    categories = db.query(models.Category).all()
    return templates.TemplateResponse("edit_item.html", {
        "request": request,
        "user": user,
        "categories": categories
    })

@app.get("/edit/{item_id}")
async def edit_item_page(request: Request, item_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    categories = db.query(models.Category).all()
    return templates.TemplateResponse(
        "edit_item.html",
        {
            "request": request,
            "item": item,
            "categories": categories,
            "user": user
        }
    )

@app.post("/edit/{item_id}")
async def edit_item(
    request: Request,
    item_id: int,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    condition: str = Form(...),
    category: str = Form(...),
    is_sold: bool = Form(False),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 检查或创建分类
    db_category = db.query(models.Category).filter(models.Category.name == category).first()
    if not db_category:
        db_category = models.Category(name=category)
        db.add(db_category)
        db.commit()
        db.refresh(db_category)

    # 更新商品信息
    item.title = title
    item.description = description
    item.price = price
    item.condition = condition
    item.category_id = db_category.id
    item.is_sold = is_sold

    # 处理新上传的图片
    if images:
        for image in images:
            if image.filename and image.content_type.startswith('image/'):
                try:
                    image_url = await ImageUploader.upload_image(image)
                    if image_url:
                        db_image = models.ItemImage(
                            image_url=image_url,
                            item_id=item_id
                        )
                        db.add(db_image)
                except Exception as e:
                    print(f"Error uploading image: {str(e)}")

    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/add-item")
async def add_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    condition: str = Form(...),
    category_id: int = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 验证分类是否存在
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    item = models.Item(
        title=title,
        description=description,
        price=price,
        condition=condition,
        category_id=category_id,
        user_id=1
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    for image in images:
        if image.content_type.startswith('image/'):
            try:
                image_url = await ImageUploader.upload_image(image)
                if image_url:
                    db_image = models.ItemImage(
                        image_url=image_url,
                        item_id=item.id
                    )
                    db.add(db_image)
            except Exception as e:
                print(f"Error uploading image: {str(e)}")
    
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete/{item_id}")
async def delete_item(request: Request, item_id: int, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/import-products")
async def import_products(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    data_dir = os.path.join(os.path.dirname(__file__), "static", "data")
    try:
        MarkdownImporter.import_to_database(data_dir, db)
        return {"message": "Products imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export-database")
async def export_database(request: Request):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        export_path = DatabaseExporter.export_to_json()
        return FileResponse(
            path=export_path,
            filename=os.path.basename(export_path),
            media_type='application/json'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import-database")
async def import_database(
    request: Request,
    file: UploadFile = File(...),
):
    user = await get_current_user(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 创建临时文件
    temp_file = f"temp_import_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        # 保存上传的文件
        with open(temp_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 导入数据
        success = DatabaseExporter.import_from_json(temp_file)
        
        return {"message": "Database imported successfully" if success else "Import failed"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

# 初始化数据库并添加示例商品
def init_db(db: Session):
    # 检查是否已有数据
    if db.query(models.Item).first() is None:
        sample_item = models.Item(
            title="Lastik Şişirme Aparatı",
            description="Araç lastiklerini şişirmek için aparat",
            price=100.0,
            condition="Yeni",
            category_id=1,
            user_id=1
        )
        db.add(sample_item)
        db.commit()
        db.refresh(sample_item)
        
        # 添加示例图片
        sample_image = models.ItemImage(
            image_url="https://example.com/sample.jpg",
            item_id=sample_item.id
        )
        db.add(sample_image)
        db.commit()

# 启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    init_db(db)
    db.close()
