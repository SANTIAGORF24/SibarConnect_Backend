from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CompanyStickerBase(BaseModel):
    name: str


class CompanyStickerCreate(CompanyStickerBase):
    company_id: int
    file_path: str
    url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class CompanyStickerOut(CompanyStickerBase):
    id: int
    company_id: int
    file_path: str
    url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
