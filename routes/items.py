import time
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import get_db
from supabase import Client
from utils.template_filters import format_datetime
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["format_datetime"] = format_datetime

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, category_id: int = None, db: Client = Depends(get_db)):
    s1 = time.time()
    print(s1)
    
    # 获取用户信息
    user = request.session.get("user")
    
    # 获取分类列表和每个分类的物品数量
    categories = db.from_("categories").select("*").execute()
    
    # 获取每个分类的物品数量
    category_counts = {}
    for category in categories.data:
        count = db.from_("items").select("id", count="exact").eq("category_id", category["id"]).execute()
        category_counts[category["id"]] = count.count
    
    # 添加物品数量到分类数据中
    for category in categories.data:
        category["item_count"] = category_counts.get(category["id"], 0)
    
    # 构建查询
    query = db.from_("items").select("id, title, description, price, is_sold, category_id")
    if category_id:
        query = query.eq("category_id", category_id)
    
    # 按照未售出优先排序，然后按ID倒序
    items = query.order("is_sold", nullsfirst=True).order("id", desc=True).execute()
    
    # 获取所有物品的ID列表
    item_ids = [item["id"] for item in items.data]
    
    # 批量获取图片和点赞数
    if item_ids:
        # 获取每个物品的第一张图片
        images = db.from_("item_images") \
            .select("item_id, image_url") \
            .in_("item_id", item_ids) \
            .execute()
        
        # 创建图片映射 {item_id: first_image_url}
        image_map = {}
        for img in images.data:
            if img["item_id"] not in image_map:
                image_map[img["item_id"]] = img["image_url"]
        
        # 批量获取点赞数
        likes = db.from_("likes") \
            .select("item_id, id") \
            .in_("item_id", item_ids) \
            .execute()
        
        # 创建点赞数映射 {item_id: likes_count}
        likes_map = {}
        for like in likes.data:
            likes_map[like["item_id"]] = likes_map.get(like["item_id"], 0) + 1
    else:
        image_map = {}
        likes_map = {}
    
    # 处理物品数据
    for item in items.data:
        item["first_image"] = image_map.get(item["id"])
        item["likes_count"] = likes_map.get(item["id"], 0)
    
    print(time.time()-s1)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "items": items.data,
            "categories": categories.data,
            "user": user,
            "current_category": category_id
        }
    )

@router.get("/item/{item_id}")
async def item_detail(request: Request, item_id: int, db: Client = Depends(get_db)):
    # 获取用户信息
    user = request.session.get("user")
    ip_address = request.client.host
    
    # 获取商品详情、图片和评论
    query = db.from_("items").select("*, categories(name)").eq("id", item_id).execute()
    if not query.data:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item = query.data[0]
    
    # 并行获取图片、评论和点赞信息
    images = db.from_("item_images").select("*").eq("item_id", item_id).execute()
    comments = db.from_("comments").select("*").eq("item_id", item_id).order("created_at", desc=True).execute()
    likes = db.from_("likes").select("id").eq("item_id", item_id).execute()
    user_like = db.from_("likes").select("id").eq("item_id", item_id).eq("ip_address", ip_address).execute()
    
    # 添加图片到物品数据
    item["images"] = images.data
    
    return templates.TemplateResponse(
        "item_detail.html",
        {
            "request": request,
            "item": item,
            "user": user,
            "comments": comments.data,
            "likes_count": len(likes.data),
            "user_liked": len(user_like.data) > 0
        }
    )

@router.post("/api/items/{item_id}/like")
async def like_item(
    request: Request,
    item_id: int,
    db: Client = Depends(get_db)
):
    # 获取用户信息
    user = request.session.get("user")
    if not user:
        return JSONResponse(status_code=401, content={"message": "Unauthorized"})
    
    try:
        # 检查是否已经点赞
        existing_like = db.from_("likes").select("*").eq("item_id", item_id).eq("user_id", user["id"]).execute()
        
        if existing_like.data:
            # 如果已经点赞，则取消点赞
            db.from_("likes").delete().eq("item_id", item_id).eq("user_id", user["id"]).execute()
            is_liked = False
        else:
            # 如果没有点赞，则添加点赞
            db.from_("likes").insert({
                "item_id": item_id,
                "user_id": user["id"],
                "ip_address": request.client.host,
                "created_at": datetime.datetime.utcnow().isoformat()
            }).execute()
            is_liked = True
        
        # 获取最新的点赞数
        likes_count = db.from_("likes").select("*", count="exact").eq("item_id", item_id).execute()
        
        return JSONResponse(content={
            "success": True,
            "is_liked": is_liked,
            "likes_count": likes_count.count
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
