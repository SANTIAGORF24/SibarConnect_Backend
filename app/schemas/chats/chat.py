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


class ChatInsightsMessage(BaseModel):
    id: int | None = None
    content: str
    message_type: str = "text"
    direction: str | None = None
    created_at: datetime | None = None


class ChatInsightsRequest(BaseModel):
    chat_id: int
    limit: int = 100
    messages: List[ChatInsightsMessage] | None = None


class MessageSentiment(BaseModel):
    id: int | None = None
    content: str | None = None
    sentiment: str
    score: float


class ChatSentiment(BaseModel):
    label: str
    score: float
    trend: str


class ExtractedEntity(BaseModel):
    type: str
    value: str


class SuggestedAction(BaseModel):
    action: str
    reason: str | None = None


class ChatInsightsOut(BaseModel):
    message_sentiments: List[MessageSentiment] = []
    chat_sentiment: ChatSentiment | None = None
    intents: List[str] = []
    entities: List[ExtractedEntity] = []
    suggested_actions: List[SuggestedAction] = []
    suggested_reply: str | None = None
    tone_warnings: List[str] = []
    interest_probability: float | None = None
    churn_risk: float | None = None


class AssistDraftRequest(BaseModel):
    chat_id: int
    draft: str


class AssistDraftOut(BaseModel):
    improved: str
    tone_warnings: List[str] = []


class ChatFilterParams(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    has_appointment: Optional[bool] = None
    has_response: Optional[bool] = None
    last_days: Optional[int] = None
    q: Optional[str] = None
    tag_ids: Optional[List[int]] = None
    pinned_by_user_id: Optional[int] = None
    exclude_snoozed_for_user_id: Optional[int] = None


class TagOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class StartChatRequest(BaseModel):
    phone_number: str
    content: str
    message_type: str = "text"
    customer_name: Optional[str] = None


class TagCreate(BaseModel):
    name: str


class NoteOut(BaseModel):
    id: int
    chat_id: int
    user_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class StartChatTemplateRequest(BaseModel):
    phone_number: str
    template_name: str
    language_code: str
    body_params: List[str] | None = None
    customer_name: Optional[str] = None