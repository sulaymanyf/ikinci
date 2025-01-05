from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from supabase import Client

router = APIRouter(prefix="/api")

class CommentCreate(BaseModel):
    commenter_name: str
    content: str

@router.post("/items/{item_id}/comments")
async def create_comment(
    request: Request,
    item_id: int,
    comment: CommentCreate,
    db: Client = Depends(get_db)
):
    comment_data = {
        "item_id": item_id,
        "content": comment.content,
        "created_at": datetime.utcnow().isoformat(),
        "commenter_name": comment.commenter_name or "Anonim",  # 如果没有提供名称，使用"匿名"
        "username": None  # 将 username 设置为 NULL
    }
    
    # 如果用户已登录，记录用户ID和用户名（可选）
    user = request.session.get("user")
    if user and "id" in user:
        comment_data["user_id"] = user["id"]
        if "username" in user:
            comment_data["username"] = user["username"]
    
    result = db.from_("comments").insert(comment_data).execute()
    return result.data[0]

@router.get("/items/{item_id}/likes")
async def get_likes(item_id: int, db: Client = Depends(get_db)):
    likes = db.from_("likes").select("id").eq("item_id", item_id).execute()
    return {"likes_count": len(likes.data)}

@router.post("/items/{item_id}/likes")
async def toggle_like(
    request: Request,
    item_id: int,
    db: Client = Depends(get_db)
):
    ip_address = request.client.host
    
    # 检查是否已经点赞
    existing_like = db.from_("likes") \
        .select("id") \
        .eq("item_id", item_id) \
        .eq("ip_address", ip_address) \
        .execute()
    
    if existing_like.data:
        # 如果已经点赞，则取消点赞
        db.from_("likes") \
            .delete() \
            .eq("id", existing_like.data[0]["id"]) \
            .execute()
        return {"liked": False}
    
    # 如果未点赞，则添加点赞
    like_data = {
        "item_id": item_id,
        "ip_address": ip_address,
        "created_at": datetime.utcnow().isoformat()
    }
    db.from_("likes").insert(like_data).execute()
    return {"liked": True}

@router.post("/items/{item_id}/toggle_sold")
async def toggle_sold_status(
    request: Request,
    item_id: int,
    db: Client = Depends(get_db)
):
    if "user" not in request.session or not request.session["user"].get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 获取当前状态
    item = db.from_("items").select("is_sold").eq("id", item_id).execute()
    if not item.data:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # 切换状态
    current_status = item.data[0]["is_sold"]
    db.from_("items").update({"is_sold": not current_status}).eq("id", item_id).execute()
    
    return {"status": "success"}

@router.get("/categories")
async def get_categories(db: Client = Depends(get_db)):
    """获取所有分类"""
    try:
        result = db.from_("categories").select("*").order("name").execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
