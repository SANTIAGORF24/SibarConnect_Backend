from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship("TemplateItem", back_populates="template", cascade="all, delete-orphan", order_by="TemplateItem.order_index")


class TemplateItem(Base):
    __tablename__ = "template_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    item_type = Column(String(20), nullable=False)
    text_content = Column(Text, nullable=True)
    media_url = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    caption = Column(String(500), nullable=True)

    template = relationship("Template", back_populates="items")


