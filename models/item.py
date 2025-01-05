from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ItemBase(BaseModel):
    title: str
    description: str
    price: float
    category_id: int
    is_sold: bool = False

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class ItemImage(BaseModel):
    id: int
    item_id: int
    image_url: str
    
    class Config:
        orm_mode = True

class ItemDetail(Item):
    images: List[ItemImage]
    category: Optional[dict]
    likes_count: int = 0
