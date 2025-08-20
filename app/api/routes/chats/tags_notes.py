from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.chats import (
    list_tags,
    create_tag,
    delete_tag,
    set_chat_tags,
    list_chat_tags,
    add_note,
    list_notes,
)
from app.schemas.chats.chat import TagOut, TagCreate, NoteOut

router = APIRouter()


@router.get("/tags", response_model=List[TagOut])
def list_company_tags(company_id: int, db: Session = Depends(get_db)):
    rows = list_tags(db, company_id)
    return rows


@router.post("/tags", response_model=TagOut)
def create_company_tag(company_id: int, payload: TagCreate, db: Session = Depends(get_db)):
    row = create_tag(db, company_id, payload.name)
    return row


@router.delete("/tags/{tag_id}")
def delete_company_tag(tag_id: int, company_id: int, db: Session = Depends(get_db)):
    ok = delete_tag(db, company_id, tag_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Etiqueta no encontrada")
    return {"success": True}


@router.get("/{chat_id}/tags", response_model=List[int])
def list_tags_for_chat(chat_id: int, db: Session = Depends(get_db)):
    return list_chat_tags(db, chat_id)


@router.put("/{chat_id}/tags")
def set_tags_for_chat(chat_id: int, tag_ids: List[int], db: Session = Depends(get_db)):
    set_chat_tags(db, chat_id, tag_ids)
    return {"success": True}


@router.post("/{chat_id}/notes", response_model=NoteOut)
def add_note_to_chat(chat_id: int, company_id: int, user_id: int, content: str, db: Session = Depends(get_db)):
    note = add_note(db, company_id, chat_id, user_id, content)
    return note


@router.get("/{chat_id}/notes", response_model=List[NoteOut])
def list_chat_notes(chat_id: int, company_id: int, db: Session = Depends(get_db)):
    rows = list_notes(db, company_id, chat_id)
    return rows


