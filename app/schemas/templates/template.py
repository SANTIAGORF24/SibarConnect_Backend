from pydantic import BaseModel, Field
from typing import List, Literal, Optional


TemplateItemType = Literal["text", "image", "video", "audio", "document"]


class TemplateItemCreate(BaseModel):
    order_index: int
    item_type: TemplateItemType
    text_content: Optional[str] = None
    media_url: Optional[str] = None
    mime_type: Optional[str] = None
    caption: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1)
    items: List[TemplateItemCreate]


class TemplateItemOut(BaseModel):
    id: int
    order_index: int
    item_type: TemplateItemType
    text_content: Optional[str]
    media_url: Optional[str]
    mime_type: Optional[str]
    caption: Optional[str]

    class Config:
        orm_mode = True


class TemplateOut(BaseModel):
    id: int
    company_id: int
    name: str
    items: List[TemplateItemOut]

    class Config:
        orm_mode = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    items: Optional[List[TemplateItemCreate]] = None


