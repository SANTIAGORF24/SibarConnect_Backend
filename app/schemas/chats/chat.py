from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MessageBase(BaseModel):
    content: str
    message_type: str = "text"
    direction: str  # incoming, outgoing
    sender_name: Optional[str] = None


class MessageCreate(MessageBase):
    chat_id: int
    user_id: Optional[int] = None
    whatsapp_message_id: Optional[str] = None
    wamid: Optional[str] = None
    attachment_url: Optional[str] = None
    timestamp: Optional[datetime] = None


class MessageOut(MessageBase):
    id: int
    chat_id: int
    user_id: Optional[int] = None
    whatsapp_message_id: Optional[str] = None
    wamid: Optional[str] = None
    status: str
    attachment_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatBase(BaseModel):
    phone_number: str
    customer_name: Optional[str] = None
    status: str = "active"
    priority: str = "low"


class ChatCreate(ChatBase):
    company_id: int
    assigned_user_id: Optional[int] = None


class ChatOut(ChatBase):
    id: int
    company_id: int
    assigned_user_id: Optional[int] = None
    last_message_time: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Incluir los últimos mensajes
    messages: List[MessageOut] = []
    
    class Config:
        from_attributes = True


class ChatWithLastMessage(ChatBase):
    id: int
    company_id: int
    assigned_user_id: Optional[int] = None
    last_message_time: datetime
    created_at: datetime
    
    # Solo el último mensaje para la lista de chats
    last_message: Optional[MessageOut] = None
    unread_count: int = 0
    
    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    chat_id: int
    content: str
    message_type: str = "text"


class SendMediaLinkRequest(BaseModel):
    chat_id: int
    media_url: str
    message_type: str
    caption: Optional[str] = None


class ChatAssignRequest(BaseModel):
    chat_id: int
    assigned_user_id: int
    priority: str


class ChatStatusUpdate(BaseModel):
    chat_id: int
    status: str


class CreateAppointmentRequest(BaseModel):
    chat_id: int
    assigned_user_id: int
    start_at: datetime


class CreateSummaryRequest(BaseModel):
    chat_id: int
