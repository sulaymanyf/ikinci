from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

class ItemBase(BaseModel):
    title: str
    description: str
    price: float
    condition: str
    category_id: int
    is_sold: bool = False

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    created_at: datetime = Field(default_factory=datetime.now)
    images: List["ItemImageResponse"] = []

    class Config:
        from_attributes = True

class ItemImageBase(BaseModel):
    image_url: str
    item_id: int

class ItemImageCreate(ItemImageBase):
    pass

class ItemImageResponse(ItemImageBase):
    id: int
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

# 更新 ItemResponse 的 images 字段的前向引用
ItemResponse.model_rebuild()

class VisitStats(BaseModel):
    total_visits: int = 0
    last_reset: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True