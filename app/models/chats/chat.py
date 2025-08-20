from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), nullable=False)  # Número de teléfono del cliente
    customer_name = Column(String(255), nullable=True)  # Nombre del cliente
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Agente asignado
    status = Column(String(20), default="active")  # active, closed, pending
    priority = Column(String(10), default="low")  # low, medium, high
    last_message_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    company = relationship("Company", back_populates="chats")
    assigned_user = relationship("User")
    messages = relationship("Message", back_populates="chat", order_by="Message.created_at")


class ChatSummary(Base):
    __tablename__ = "chat_summaries"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    summary = Column(Text, nullable=False)
    interest = Column(String(20), default="Indeciso")  # Interesado, No interesado, Indeciso
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    provider = Column(String(50), default="gemini")
    model = Column(String(50), default="gemini-2.5-flash")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, document, etc.
    direction = Column(String(10), nullable=False)  # incoming, outgoing
    sender_name = Column(String(255), nullable=True)  # Nombre del que envía
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Si es outgoing, qué usuario lo envió
    whatsapp_message_id = Column(String(255), nullable=True)  # ID de WhatsApp
    wamid = Column(String(255), nullable=True)  # WAMID de WhatsApp
    status = Column(String(20), default="sent")  # sent, delivered, read, failed
    attachment_url = Column(String(500), nullable=True)  # URL del archivo multimedia
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    chat = relationship("Chat", back_populates="messages")
    user = relationship("User")  # Usuario que envió el mensaje (si es outgoing)


class ChatTag(Base):
    __tablename__ = "chat_tags"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(64), nullable=False)


class ChatTagMap(Base):
    __tablename__ = "chat_tag_map"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("chat_tags.id"), nullable=False)


class ChatNote(Base):
    __tablename__ = "chat_notes"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatPin(Base):
    __tablename__ = "chat_pins"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatSnooze(Base):
    __tablename__ = "chat_snoozes"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    until_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatAudit(Base):
    __tablename__ = "chat_audit"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())