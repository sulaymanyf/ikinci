from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List
from datetime import datetime
import uuid
import os
from database import get_db
from supabase import Client

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_admin(request: Request):
    """检查用户是否是管理员"""
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Client = Depends(get_db)):
    user = check_admin(request)
    
    categories = db.table("categories").select("*").execute()
    items = db.table("items").select("*, categories(name)").execute()
    
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "categories": categories.data,
            "items": items.data,
            "user": user
        }
    )

@router.post("/admin/items")
async def create_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    images: List[UploadFile] = File(...),
    db: Client = Depends(get_db)
):
    user = check_admin(request)
    
    # 创建商品
    item_data = {
        "title": title,
        "description": description,
        "price": price,
        "category_id": category_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = db.table("items").insert(item_data).execute()
    item_id = result.data[0]["id"]
    
    # 处理图片
    for image in images:
        if image.filename:
            # 生成唯一文件名
            ext = os.path.splitext(image.filename)[1]
            filename = f"{uuid.uuid4()}{ext}"
            
            # 保存图片
            with open(f"static/uploads/{filename}", "wb") as buffer:
                content = await image.read()
                buffer.write(content)
            
            # 保存图片信息到数据库
            image_data = {
                "item_id": item_id,
                "image_url": f"/static/uploads/{filename}"
            }
            db.table("item_images").insert(image_data).execute()
    
    return RedirectResponse(url="/admin", status_code=303)

@router.get("/edit_item/{item_id}", response_class=HTMLResponse)
async def edit_item_page(request: Request, item_id: int, db: Client = Depends(get_db)):
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    # 获取商品信息
    item = db.table("items").select("*").eq("id", item_id).execute()
    if not item.data:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # 获取商品图片
    images = db.table("item_images").select("*").eq("item_id", item_id).execute()
    
    # 获取所有分类
    categories = db.table("categories").select("*").execute()
    
    return templates.TemplateResponse(
        "edit_item.html",
        {
            "request": request,
            "item": item.data[0],
            "images": images.data,
            "categories": categories.data,
            "user": user
        }
    )

@router.post("/edit_item/{item_id}")
async def edit_item(
    request: Request,
    item_id: int,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    new_price: float = Form(None),
    condition: str = Form(...),
    category_id: int = Form(...),
    deleted_images: str = Form(""),
    images: list[UploadFile] = File(None),
    db: Client = Depends(get_db)
):
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return JSONResponse(status_code=403, content={"message": "Unauthorized"})
    
    try:
        # 更新商品信息
        item_data = {
            "title": title,
            "description": description,
            "price": price,
            "category_id": category_id,
            "condition": condition
        }
        
        if new_price is not None and new_price != "":
            item_data["new_price"] = float(new_price)
        else:
            item_data["new_price"] = None  # 如果没有新价格，设置为 NULL
        
        db.table("items").update(item_data).eq("id", item_id).execute()
        
        # 处理删除的图片
        if deleted_images:
            deleted_ids = [int(id) for id in deleted_images.split(",") if id]
            for image_id in deleted_ids:
                # 获取图片信息
                image = db.table("item_images").select("image_url").eq("id", image_id).execute()
                if image.data:
                    # 删除文件
                    file_path = os.path.join(os.path.dirname(__file__), "..", image.data[0]["image_url"].lstrip("/"))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # 从数据库中删除
                    db.table("item_images").delete().eq("id", image_id).execute()
        
        # 处理新上传的图片
        if images:
            for image in images:
                if image.filename:
                    # 生成唯一文件名
                    file_extension = os.path.splitext(image.filename)[1]
                    unique_filename = f"{uuid.uuid4()}{file_extension}"
                    file_path = os.path.join("static/uploads", unique_filename)
                    
                    # 保存文件
                    with open(file_path, "wb") as buffer:
                        content = await image.read()
                        buffer.write(content)
                    
                    # 保存到数据库
                    db.table("item_images").insert({
                        "item_id": item_id,
                        "image_url": f"/static/uploads/{unique_filename}"
                    }).execute()
        
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@router.get("/add_item", response_class=HTMLResponse)
async def add_item_page(request: Request, db: Client = Depends(get_db)):
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    # 获取所有分类
    categories = db.table("categories").select("*").execute()
    
    # 创建空的商品数据
    item = {
        "id": None,
        "title": "",
        "description": "",
        "price": "",
        "category_id": None
    }
    
    return templates.TemplateResponse(
        "edit_item.html",
        {
            "request": request,
            "item": item,
            "images": [],
            "categories": categories.data,
            "user": user,
            "is_new": True
        }
    )

@router.post("/add_item")
async def add_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    new_price: float = Form(None),
    condition: str = Form(...),
    category_id: int = Form(...),
    images: list[UploadFile] = File(None),
    db: Client = Depends(get_db)
):
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return JSONResponse(status_code=403, content={"message": "Unauthorized"})
    
    try:
        # 创建新商品
        item_data = {
            "title": title,
            "description": description,
            "price": price,
            "category_id": category_id,
            "condition": condition,
            "is_sold": False
        }
        
        if new_price is not None and new_price != "":
            item_data["new_price"] = float(new_price)
            
        # 插入商品
        result = db.table("items").insert(item_data).execute()
        
        if not result.data:
            raise Exception("Failed to create item")
            
        item_id = result.data[0]["id"]
        
        # 处理上传的图片
        if images:
            for image in images:
                if image.filename:
                    # 生成唯一文件名
                    file_extension = os.path.splitext(image.filename)[1]
                    unique_filename = f"{uuid.uuid4()}{file_extension}"
                    file_path = os.path.join("static/uploads", unique_filename)
                    
                    # 保存文件
                    with open(file_path, "wb") as buffer:
                        content = await image.read()
                        buffer.write(content)
                    
                    # 保存到数据库
                    db.table("item_images").insert({
                        "item_id": item_id,
                        "image_url": f"/static/uploads/{unique_filename}"
                    }).execute()
        
        return JSONResponse(content={"success": True, "item_id": item_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@router.delete("/api/items/{item_id}")
async def delete_item(
    request: Request,
    item_id: int,
    db: Client = Depends(get_db)
):
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return JSONResponse(status_code=403, content={"message": "Unauthorized"})
    
    try:
        # 获取商品的所有图片
        images = db.table("item_images").select("*").eq("item_id", item_id).execute()
        
        # 删除图片文件
        for image in images.data:
            file_path = os.path.join(os.path.dirname(__file__), "..", image["image_url"].lstrip("/"))
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 删除数据库中的图片记录
        db.table("item_images").delete().eq("item_id", item_id).execute()
        
        # 删除商品的评论
        db.table("comments").delete().eq("item_id", item_id).execute()
        
        # 删除商品的点赞
        db.table("likes").delete().eq("item_id", item_id).execute()
        
        # 删除商品
        result = db.table("items").delete().eq("id", item_id).execute()
        
        if not result.data:
            return JSONResponse(
                status_code=404,
                content={"message": "Item not found"}
            )
        
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": str(e)}
        )

@router.get("/categories")
async def categories_page(
    request: Request,
    db: Client = Depends(get_db)
):
    """分类管理页面"""
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    # 获取所有分类
    categories = db.table("categories").select("*").execute()
    
    # 获取每个分类的商品数量
    for category in categories.data:
        items_count = db.table("items").select("id", count="exact").eq("category_id", category["id"]).execute()
        category["items_count"] = items_count.count
    
    return templates.TemplateResponse(
        "categories.html",
        {
            "request": request,
            "categories": categories.data,
            "user": user
        }
    )

@router.post("/categories")
async def create_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Client = Depends(get_db)
):
    """创建新分类"""
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    try:
        data = {"name": name}
        if description:
            data["description"] = description
        
        print("Inserting category with data:", data)
        # 使用 upsert 操作，让数据库自动处理 ID
        result = db.table("categories").upsert(data).execute()
        print("Insert result:", result.data)
        
        # 检查是否成功插入
        if not result.data:
            raise Exception("Failed to insert category")
            
        return RedirectResponse(url="/categories", status_code=303)
    except Exception as e:
        print("Error creating category:", str(e))
        # 如果是唯一约束冲突，返回友好的错误信息
        if "duplicate key value violates unique constraint" in str(e):
            return templates.TemplateResponse(
                "categories.html",
                {
                    "request": request,
                    "error": "Bu kategori adı zaten kullanılıyor.",
                    "user": user,
                    "categories": db.table("categories").select("*").execute().data
                }
            )
        return templates.TemplateResponse(
            "categories.html",
            {
                "request": request,
                "error": str(e),
                "user": user,
                "categories": db.table("categories").select("*").execute().data
            }
        )

@router.get("/categories/{category_id}")
async def edit_category_page(
    request: Request,
    category_id: int,
    db: Client = Depends(get_db)
):
    """编辑分类页面"""
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    # 获取分类信息
    category = db.table("categories").select("*").eq("id", category_id).execute()
    if not category.data:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 获取所有分类
    categories = db.table("categories").select("*").execute()
    
    # 获取每个分类的商品数量
    for cat in categories.data:
        items_count = db.table("items").select("id", count="exact").eq("category_id", cat["id"]).execute()
        cat["items_count"] = items_count.count
    
    return templates.TemplateResponse(
        "categories.html",
        {
            "request": request,
            "categories": categories.data,
            "edit_category": category.data[0],
            "user": user
        }
    )

@router.post("/categories/{category_id}")
async def update_category(
    request: Request,
    category_id: int,
    name: str = Form(...),
    description: str = Form(None),
    db: Client = Depends(get_db)
):
    """更新分类"""
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login")
    
    try:
        data = {"name": name}
        if description:
            data["description"] = description
        
        db.table("categories").update(data).eq("id", category_id).execute()
        return RedirectResponse(url="/categories", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "categories.html",
            {
                "request": request,
                "error": str(e),
                "user": user
            }
        )

@router.delete("/categories/{category_id}")
async def delete_category(
    request: Request,
    category_id: int,
    db: Client = Depends(get_db)
):
    """删除分类"""
    # 检查用户是否是管理员
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        return JSONResponse(status_code=403, content={"message": "Unauthorized"})
    
    try:
        # 检查是否有商品使用此分类
        items = db.table("items").select("id").eq("category_id", category_id).execute()
        if items.data:
            return JSONResponse(
                status_code=400,
                content={"message": "Cannot delete category that has items"}
            )
        
        # 删除分类
        db.table("categories").delete().eq("id", category_id).execute()
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": str(e)}
        )
