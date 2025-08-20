from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.services.chats import (
    get_chats_by_company,
    get_chat_by_id,
    assign_chat,
    update_chat_status,
    pin_chat,
    unpin_chat,
    snooze_chat,
    unsnooze_chat,
    bulk_update_chats,
    bulk_set_tags_for_chats,
)
from app.schemas.chats.chat import (
    ChatWithLastMessage,
    ChatOut,
    ChatAssignRequest,
    ChatStatusUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[ChatWithLastMessage])
def get_company_chats(
    company_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    has_appointment: Optional[bool] = None,
    has_response: Optional[bool] = None,
    last_days: Optional[int] = None,
    q: Optional[str] = None,
    tag_ids: Optional[str] = None,
    pinned_by_user_id: Optional[int] = None,
    exclude_snoozed_for_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    tag_list: Optional[List[int]] = None
    if tag_ids:
        try:
            tag_list = [int(x) for x in tag_ids.split(",") if x]
        except Exception:
            tag_list = None
    chats = get_chats_by_company(
        db,
        company_id,
        status=status,
        priority=priority,
        has_appointment=has_appointment,
        has_response=has_response,
        last_days=last_days,
        q=q,
        tag_ids=tag_list,
        pinned_by_user_id=pinned_by_user_id,
        exclude_snoozed_for_user_id=exclude_snoozed_for_user_id,
    )
    return chats


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(
    chat_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    chat = get_chat_by_id(db, chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    return ChatOut.from_orm(chat)


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    from app.models.chats.chat import Chat, Message
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.company_id == company_id
    ).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    try:
        db.query(Message).filter(Message.chat_id == chat_id).delete()
        db.query(Chat).filter(Chat.id == chat_id).delete()
        db.commit()
        return {"success": True, "message": "Chat eliminado exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando chat: {str(e)}")


@router.post("/assign")
def assign_chat_endpoint(
    data: ChatAssignRequest,
    company_id: int,
    db: Session = Depends(get_db)
):
    chat = assign_chat(db, company_id, data.chat_id, data.assigned_user_id, data.priority)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    return ChatOut.from_orm(chat)


@router.post("/status")
def update_status_endpoint(
    data: ChatStatusUpdate,
    company_id: int,
    db: Session = Depends(get_db)
):
    chat = update_chat_status(db, company_id, data.chat_id, data.status)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    return ChatOut.from_orm(chat)


@router.post("/{chat_id}/pin")
def pin_chat_endpoint(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    pin_chat(db, chat_id, user_id)
    return {"success": True}


@router.delete("/{chat_id}/pin")
def unpin_chat_endpoint(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    unpin_chat(db, chat_id, user_id)
    return {"success": True}


@router.post("/{chat_id}/snooze")
def snooze_chat_endpoint(chat_id: int, user_id: int, until_at: str, db: Session = Depends(get_db)):
    from datetime import datetime
    snooze_chat(db, chat_id, user_id, datetime.fromisoformat(until_at))
    return {"success": True}


@router.delete("/{chat_id}/snooze")
def unsnooze_chat_endpoint(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    unsnooze_chat(db, chat_id, user_id)
    return {"success": True}


@router.post("/bulk")
def bulk_actions(
    company_id: int,
    chat_ids: List[int],
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_user_id: Optional[int] = None,
    tag_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db)
):
    updated = bulk_update_chats(db, company_id, chat_ids, status=status, priority=priority, assigned_user_id=assigned_user_id)
    if tag_ids is not None:
        bulk_set_tags_for_chats(db, chat_ids, tag_ids)
    return {"updated": updated, "success": True}


