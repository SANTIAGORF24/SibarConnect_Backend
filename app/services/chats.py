from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, exists
from typing import List, Optional
from app.models.chats.chat import Chat, Message, ChatSummary, Appointment, ChatTag, ChatTagMap, ChatNote, ChatPin, ChatSnooze, ChatAudit
from app.schemas.chats.chat import ChatCreate, MessageCreate, ChatOut, MessageOut, ChatWithLastMessage
from app.services.realtime import manager
from fastapi.encoders import jsonable_encoder


def get_chats_by_company(db: Session, company_id: int, *,
                         status: Optional[str] = None,
                         priority: Optional[str] = None,
                         has_appointment: Optional[bool] = None,
                         has_response: Optional[bool] = None,
                         last_days: Optional[int] = None,
                         q: Optional[str] = None,
                         tag_ids: Optional[list[int]] = None,
                         pinned_by_user_id: Optional[int] = None,
                         exclude_snoozed_for_user_id: Optional[int] = None) -> List[ChatWithLastMessage]:
    filters = [Chat.company_id == company_id]
    if status:
        filters.append(Chat.status == status)
    if priority:
        filters.append(Chat.priority == priority)
    if last_days is not None and last_days > 0:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=last_days)
        filters.append(Chat.last_message_time >= cutoff)

    base_query = db.query(Chat).filter(and_(*filters))

    if has_appointment is not None:
        appt_exists = db.query(Appointment.id).filter(and_(Appointment.company_id == company_id, Appointment.chat_id == Chat.id)).exists()
        if has_appointment:
            base_query = base_query.filter(appt_exists)
        else:
            base_query = base_query.filter(~appt_exists)

    if has_response is not None:
        resp_exists = db.query(Message.id).filter(and_(Message.chat_id == Chat.id, Message.direction == 'outgoing')).exists()
        if has_response:
            base_query = base_query.filter(resp_exists)
        else:
            base_query = base_query.filter(~resp_exists)

    if q:
        q_like = f"%{q.lower()}%"
        msg_exists = db.query(Message.id).filter(and_(Message.chat_id == Chat.id, func.lower(Message.content).like(q_like))).exists()
        base_query = base_query.filter(or_(func.lower(Chat.customer_name).like(q_like), func.lower(Chat.phone_number).like(q_like), msg_exists))

    if tag_ids:
        tag_exists = db.query(ChatTagMap.id).filter(and_(ChatTagMap.chat_id == Chat.id, ChatTagMap.tag_id.in_(tag_ids))).exists()
        base_query = base_query.filter(tag_exists)

    if exclude_snoozed_for_user_id:
        from datetime import datetime
        now = datetime.utcnow()
        snoozed_exists = db.query(ChatSnooze.id).filter(and_(ChatSnooze.chat_id == Chat.id, ChatSnooze.user_id == exclude_snoozed_for_user_id, ChatSnooze.until_at > now)).exists()
        base_query = base_query.filter(~snoozed_exists)

    chats = base_query.order_by(desc(Chat.last_message_time)).all()

    pins_set: set[int] = set()
    if pinned_by_user_id:
        pinned_rows = db.query(ChatPin).filter(ChatPin.user_id == pinned_by_user_id, ChatPin.chat_id.in_([c.id for c in chats])).all()
        pins_set = {r.chat_id for r in pinned_rows}

    result: List[ChatWithLastMessage] = []
    for chat in chats:
        last_message = (
            db.query(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(desc(Message.created_at))
            .first()
        )
        unread_count = 0
        data = ChatWithLastMessage(
            id=chat.id,
            phone_number=chat.phone_number,
            customer_name=chat.customer_name,
            status=chat.status,
            priority=chat.priority,
            company_id=chat.company_id,
            assigned_user_id=chat.assigned_user_id,
            last_message_time=chat.last_message_time,
            created_at=chat.created_at,
            last_message=MessageOut.from_orm(last_message) if last_message else None,
            unread_count=unread_count
        )
        result.append(data)
    if pins_set:
        result.sort(key=lambda c: (0 if c.id in pins_set else 1, c.last_message_time if hasattr(c, 'last_message_time') else None), reverse=False)
    return result


def get_chat_by_id(db: Session, chat_id: int, company_id: int) -> Optional[Chat]:
    """Obtener un chat específico con todos sus mensajes"""
    return (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.company_id == company_id)
        .first()
    )


def get_or_create_chat(db: Session, phone_number: str, company_id: int, customer_name: str = None) -> Chat:
    """Obtener un chat existente o crear uno nuevo"""
    
    # Buscar chat existente
    existing_chat = (
        db.query(Chat)
        .filter(Chat.phone_number == phone_number, Chat.company_id == company_id)
        .first()
    )
    
    if existing_chat:
        # Actualizar nombre del cliente si se proporciona
        if customer_name and not existing_chat.customer_name:
            existing_chat.customer_name = customer_name
            db.commit()
            db.refresh(existing_chat)
        return existing_chat
    
    # Crear nuevo chat
    new_chat = Chat(
        phone_number=phone_number,
        customer_name=customer_name,
        company_id=company_id,
        status="active",
        priority="low"
    )
    
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat


def create_message(db: Session, message_data: MessageCreate) -> Message:
    """Crear un nuevo mensaje"""
    
    # Convertir a dict y remover timestamp si existe
    message_dict = message_data.model_dump()
    custom_timestamp = message_dict.pop('timestamp', None)
    
    # Crear el mensaje
    message = Message(**message_dict)
    
    # Si se proporciona un timestamp personalizado, establecerlo después de crear el objeto
    if custom_timestamp:
        message.created_at = custom_timestamp
    
    db.add(message)
    
    # Actualizar la hora del último mensaje en el chat
    chat = db.query(Chat).filter(Chat.id == message_data.chat_id).first()
    if chat:
        # Si es un mensaje importado con timestamp personalizado, usar ese
        if custom_timestamp:
            chat.last_message_time = custom_timestamp
        else:
            chat.last_message_time = func.now()
    
    db.commit()
    db.refresh(message)

    try:
        company_id = chat.company_id if chat else None
        if company_id is not None:
            payload = jsonable_encoder(MessageOut.from_orm(message))
            # Agregar company_id para que el frontend pueda validar
            payload["company_id"] = company_id
            # Emitir evento a los clientes del chat
            import anyio
            async def _broadcast() -> None:
                await manager.broadcast_to_chat(company_id, message.chat_id, "message.created", payload)
                # Emitir actualización a nivel de empresa para refrescar lista de chats
                await manager.broadcast_to_company(company_id, "chat.updated", {
                    "chat_id": message.chat_id,
                    "company_id": company_id,
                    "last_message": payload
                })
            try:
                anyio.from_thread.run(_broadcast)
            except RuntimeError:
                # Si ya estamos en un loop async, ejecutar directamente
                import asyncio
                async def _broadcast_asyncio() -> None:
                    await manager.broadcast_to_chat(company_id, message.chat_id, "message.created", payload)
                    await manager.broadcast_to_company(company_id, "chat.updated", {
                        "chat_id": message.chat_id,
                        "company_id": company_id,
                        "last_message": payload
                    })
                asyncio.create_task(_broadcast_asyncio())
    except Exception:
        # Evitar que errores de broadcast rompan la creación del mensaje
        pass
    return message


def assign_chat(db: Session, company_id: int, chat_id: int, assigned_user_id: int, priority: str) -> Optional[Chat]:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.company_id == company_id)
        .first()
    )
    if not chat:
        return None
    chat.assigned_user_id = assigned_user_id
    chat.priority = priority
    db.commit()
    db.refresh(chat)
    try:
        db.add(ChatAudit(company_id=company_id, chat_id=chat_id, user_id=assigned_user_id, action="assign", details=f"priority={priority}"))
        db.commit()
    except Exception:
        db.rollback()
    return chat


def update_chat_status(db: Session, company_id: int, chat_id: int, status: str) -> Optional[Chat]:
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.company_id == company_id)
        .first()
    )
    if not chat:
        return None
    chat.status = status
    db.commit()
    db.refresh(chat)
    try:
        db.add(ChatAudit(company_id=company_id, chat_id=chat_id, action="status", details=f"status={status}"))
        db.commit()
    except Exception:
        db.rollback()
    return chat


def create_appointment(db: Session, company_id: int, chat_id: int, assigned_user_id: int, start_at) -> Appointment | None:
    exists = (
        db.query(Appointment)
        .filter(
            Appointment.company_id == company_id,
            Appointment.assigned_user_id == assigned_user_id,
            Appointment.start_at == start_at,
        )
        .first()
    )
    if exists:
        return None
    appt = Appointment(
        company_id=company_id,
        chat_id=chat_id,
        assigned_user_id=assigned_user_id,
        start_at=start_at,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def save_chat_summary(db: Session, company_id: int, chat_id: int, summary: str, interest: str, provider: str = "gemini", model: str = "gemini-2.5-flash") -> ChatSummary:
    row = (
        db.query(ChatSummary)
        .filter(ChatSummary.company_id == company_id, ChatSummary.chat_id == chat_id)
        .first()
    )
    if row:
        row.summary = summary
        row.interest = interest
        row.provider = provider
        row.model = model
    else:
        row = ChatSummary(
            company_id=company_id,
            chat_id=chat_id,
            summary=summary,
            interest=interest,
            provider=provider,
            model=model,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row

def get_chat_summary(db: Session, company_id: int, chat_id: int) -> ChatSummary | None:
    return (
        db.query(ChatSummary)
        .filter(ChatSummary.company_id == company_id, ChatSummary.chat_id == chat_id)
        .first()
    )


def list_appointments_by_chat(db: Session, company_id: int, chat_id: int) -> list[Appointment]:
    return (
        db.query(Appointment)
        .filter(Appointment.company_id == company_id, Appointment.chat_id == chat_id)
        .order_by(Appointment.start_at)
        .all()
    )


def update_appointment(db: Session, company_id: int, appointment_id: int, *, assigned_user_id: int | None = None, start_at=None) -> Appointment | None:
    appt = (
        db.query(Appointment)
        .filter(Appointment.company_id == company_id, Appointment.id == appointment_id)
        .first()
    )
    if not appt:
        return None
    if assigned_user_id is not None:
        appt.assigned_user_id = assigned_user_id
    if start_at is not None:
        # Validación de conflicto
        exists = (
            db.query(Appointment)
            .filter(
                Appointment.company_id == company_id,
                Appointment.assigned_user_id == (assigned_user_id or appt.assigned_user_id),
                Appointment.start_at == start_at,
                Appointment.id != appointment_id,
            )
            .first()
        )
        if exists:
            return None
        appt.start_at = start_at
    db.commit()
    db.refresh(appt)
    return appt


def delete_appointment(db: Session, company_id: int, appointment_id: int) -> bool:
    appt = (
        db.query(Appointment)
        .filter(Appointment.company_id == company_id, Appointment.id == appointment_id)
        .first()
    )
    if not appt:
        return False
    db.delete(appt)
    db.commit()
    return True


def get_messages_by_chat(db: Session, chat_id: int, limit: int = 50) -> List[Message]:
    """Obtener mensajes de un chat específico"""
    return (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
        .all()
    )


def update_message_status(db: Session, whatsapp_message_id: str, status: str) -> Optional[Message]:
    """Actualizar el estado de un mensaje"""
    message = (
        db.query(Message)
        .filter(Message.whatsapp_message_id == whatsapp_message_id)
        .first()
    )
    
    if message:
        message.status = status
        db.commit()
        db.refresh(message)
    
    return message


def list_tags(db: Session, company_id: int) -> List[ChatTag]:
    return db.query(ChatTag).filter(ChatTag.company_id == company_id).order_by(ChatTag.name).all()


def create_tag(db: Session, company_id: int, name: str) -> ChatTag:
    row = ChatTag(company_id=company_id, name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_tag(db: Session, company_id: int, tag_id: int) -> bool:
    row = db.query(ChatTag).filter(ChatTag.company_id == company_id, ChatTag.id == tag_id).first()
    if not row:
        return False
    db.query(ChatTagMap).filter(ChatTagMap.tag_id == tag_id).delete()
    db.delete(row)
    db.commit()
    return True


def set_chat_tags(db: Session, chat_id: int, tag_ids: List[int]) -> None:
    db.query(ChatTagMap).filter(ChatTagMap.chat_id == chat_id).delete()
    for tid in tag_ids:
        db.add(ChatTagMap(chat_id=chat_id, tag_id=tid))
    db.commit()


def list_chat_tags(db: Session, chat_id: int) -> List[int]:
    rows = db.query(ChatTagMap).filter(ChatTagMap.chat_id == chat_id).all()
    return [r.tag_id for r in rows]


def add_note(db: Session, company_id: int, chat_id: int, user_id: int, content: str) -> ChatNote:
    note = ChatNote(company_id=company_id, chat_id=chat_id, user_id=user_id, content=content)
    db.add(note)
    db.commit()
    db.refresh(note)
    try:
        db.add(ChatAudit(company_id=company_id, chat_id=chat_id, user_id=user_id, action="note", details=content[:200]))
        db.commit()
    except Exception:
        db.rollback()
    return note


def list_notes(db: Session, company_id: int, chat_id: int) -> List[ChatNote]:
    return db.query(ChatNote).filter(ChatNote.company_id == company_id, ChatNote.chat_id == chat_id).order_by(desc(ChatNote.created_at)).all()


def pin_chat(db: Session, chat_id: int, user_id: int) -> None:
    exists_row = db.query(ChatPin).filter(ChatPin.chat_id == chat_id, ChatPin.user_id == user_id).first()
    if not exists_row:
        db.add(ChatPin(chat_id=chat_id, user_id=user_id))
        db.commit()


def unpin_chat(db: Session, chat_id: int, user_id: int) -> None:
    db.query(ChatPin).filter(ChatPin.chat_id == chat_id, ChatPin.user_id == user_id).delete()
    db.commit()


def snooze_chat(db: Session, chat_id: int, user_id: int, until_at) -> None:
    row = db.query(ChatSnooze).filter(ChatSnooze.chat_id == chat_id, ChatSnooze.user_id == user_id).first()
    if row:
        row.until_at = until_at
    else:
        db.add(ChatSnooze(chat_id=chat_id, user_id=user_id, until_at=until_at))
    db.commit()


def unsnooze_chat(db: Session, chat_id: int, user_id: int) -> None:
    db.query(ChatSnooze).filter(ChatSnooze.chat_id == chat_id, ChatSnooze.user_id == user_id).delete()
    db.commit()


def bulk_update_chats(db: Session, company_id: int, chat_ids: List[int], *, status: Optional[str] = None, priority: Optional[str] = None, assigned_user_id: Optional[int] = None) -> int:
    q = db.query(Chat).filter(Chat.company_id == company_id, Chat.id.in_(chat_ids))
    updates: dict = {}
    if status is not None:
        updates[Chat.status] = status
    if priority is not None:
        updates[Chat.priority] = priority
    if assigned_user_id is not None:
        updates[Chat.assigned_user_id] = assigned_user_id
    count = q.update(updates, synchronize_session=False) if updates else 0
    db.commit()
    return count


def bulk_set_tags_for_chats(db: Session, chat_ids: List[int], tag_ids: List[int]) -> None:
    db.query(ChatTagMap).filter(ChatTagMap.chat_id.in_(chat_ids)).delete(synchronize_session=False)
    for cid in chat_ids:
        for tid in tag_ids:
            db.add(ChatTagMap(chat_id=cid, tag_id=tid))
    db.commit()


def list_appointments_by_user(db: Session, company_id: int, user_id: int, date_from, date_to) -> List[Appointment]:
    return (
        db.query(Appointment)
        .filter(
            Appointment.company_id == company_id,
            Appointment.assigned_user_id == user_id,
            Appointment.start_at >= date_from,
            Appointment.start_at <= date_to,
        )
        .order_by(Appointment.start_at)
        .all()
    )


def suggest_free_slots(db: Session, company_id: int, user_id: int, *, date, start_hour: int, end_hour: int, slot_minutes: int = 30, max_slots: int = 5) -> List[str]:
    from datetime import datetime, timedelta
    day_start = datetime.combine(date, datetime.min.time()).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    day_end = datetime.combine(date, datetime.min.time()).replace(hour=end_hour, minute=0, second=0, microsecond=0)
    appts = list_appointments_by_user(db, company_id, user_id, day_start, day_end)
    busy = [(a.start_at, a.start_at + timedelta(minutes=slot_minutes)) for a in appts]
    slots: List[str] = []
    cur = day_start
    while cur + timedelta(minutes=slot_minutes) <= day_end and len(slots) < max_slots:
        end = cur + timedelta(minutes=slot_minutes)
        overlaps = any(not (end <= b_start or cur >= b_end) for b_start, b_end in busy)
        if not overlaps:
            slots.append(cur.isoformat())
        cur += timedelta(minutes=slot_minutes)
    return slots
