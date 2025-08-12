from sqlalchemy import String, Boolean, Integer, DateTime, func, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Company(Base):
  __tablename__ = "companies"
  __table_args__ = (
    UniqueConstraint("nit", name="uq_companies_nit"),
  )

  id: Mapped[int] = mapped_column(primary_key=True, index=True)
  nombre: Mapped[str] = mapped_column(String(255), index=True)
  razon_social: Mapped[str] = mapped_column(String(255))
  nit: Mapped[str] = mapped_column(String(64), unique=True, index=True)
  responsable: Mapped[str] = mapped_column(String(255))
  activa: Mapped[bool] = mapped_column(Boolean, default=True)
  cantidad_usuarios: Mapped[int] = mapped_column(Integer, default=0)
  email: Mapped[str] = mapped_column(String(255))
  telefono: Mapped[str] = mapped_column(String(64))
  direccion: Mapped[str] = mapped_column(String(255))
  created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
  
  # YCloud / WhatsApp Integration
  ycloud_api_key: Mapped[str] = mapped_column(Text, nullable=True)
  ycloud_webhook_url: Mapped[str] = mapped_column(String(500), nullable=True)
  whatsapp_phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
  
  # Relaciones
  chats = relationship("Chat", back_populates="company")
  # stickers = relationship("CompanySticker", back_populates="company")  # Temporalmente comentado


