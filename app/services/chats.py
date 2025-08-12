from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from app.models.chats.chat import Chat, Message
from app.schemas.chats.chat import ChatCreate, MessageCreate, ChatOut, MessageOut, ChatWithLastMessage


def get_chats_by_company(db: Session, company_id: int) -> List[ChatWithLastMessage]:
    """Obtener todos los chats de una empresa con el último mensaje"""
    
    # Subconsulta para obtener el último mensaje de cada chat
    latest_message_subq = (
        db.query(
            Message.chat_id,
            func.max(Message.created_at).label('latest_time')
        )
        .group_by(Message.chat_id)
        .subquery()
    )
    
    # Consulta principal con joins
    chats = (
        db.query(Chat)
        .filter(Chat.company_id == company_id)
        .order_by(desc(Chat.last_message_time))
        .all()
    )
    
    result = []
    for chat in chats:
        # Obtener el último mensaje
        last_message = (
            db.query(Message)
            .filter(Message.chat_id == chat.id)
            .order_by(desc(Message.created_at))
            .first()
        )
        
        # Contar mensajes no leídos (esto se puede implementar más tarde)
        unread_count = 0
        
        chat_data = ChatWithLastMessage(
            id=chat.id,
            phone_number=chat.phone_number,
            customer_name=chat.customer_name,
            status=chat.status,
            company_id=chat.company_id,
            assigned_user_id=chat.assigned_user_id,
            last_message_time=chat.last_message_time,
            created_at=chat.created_at,
            last_message=MessageOut.from_orm(last_message) if last_message else None,
            unread_count=unread_count
        )
        result.append(chat_data)
    
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
        status="active"
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
    return message


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
