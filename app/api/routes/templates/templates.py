from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import uuid
from app.db.session import get_db
from app.models.templates.template import Template, TemplateItem
from app.schemas.templates.template import TemplateCreate, TemplateOut, TemplateUpdate

router = APIRouter()


@router.get("/", response_model=List[TemplateOut])
def list_templates(company_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Template)
        .filter(Template.company_id == company_id)
        .order_by(Template.id.desc())
        .all()
    )
    return rows


@router.post("/", response_model=TemplateOut)
def create_template(payload: TemplateCreate, company_id: int, db: Session = Depends(get_db)):
    tpl = Template(company_id=company_id, name=payload.name)
    db.add(tpl)
    db.flush()
    for it in payload.items:
        item = TemplateItem(
            template_id=tpl.id,
            order_index=it.order_index,
            item_type=it.item_type,
            text_content=it.text_content,
            media_url=it.media_url,
            mime_type=it.mime_type,
            caption=it.caption,
        )
        db.add(item)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, payload: TemplateUpdate, company_id: int, db: Session = Depends(get_db)):
    tpl = (
        db.query(Template)
        .filter(Template.id == template_id, Template.company_id == company_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    if payload.name is not None:
        tpl.name = payload.name
    if payload.items is not None:
        db.query(TemplateItem).filter(TemplateItem.template_id == tpl.id).delete()
        for it in payload.items:
            db.add(
                TemplateItem(
                    template_id=tpl.id,
                    order_index=it.order_index,
                    item_type=it.item_type,
                    text_content=it.text_content,
                    media_url=it.media_url,
                    mime_type=it.mime_type,
                    caption=it.caption,
                )
            )
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}")
def delete_template(template_id: int, company_id: int, db: Session = Depends(get_db)):
    tpl = (
        db.query(Template)
        .filter(Template.id == template_id, Template.company_id == company_id)
        .first()
    )
    if not tpl:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    db.delete(tpl)
    db.commit()
    return {"success": True}


@router.post("/upload")
def upload_template_media(
    company_id: int,
    file: UploadFile = File(...),
    caption: str = Form("")
):
    ext = Path(file.filename).suffix.lower()
    media_dir = Path(f"media/company_{company_id}/templates")
    media_dir.mkdir(parents=True, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = media_dir / unique_filename
    content = file.file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return {
        "file_url": f"/media/company_{company_id}/templates/{unique_filename}",
        "mime_type": file.content_type,
        "caption": caption,
    }


