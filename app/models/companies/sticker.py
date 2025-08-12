from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class CompanySticker(Base):
    __tablename__ = "company_stickers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    # company = relationship("Company", back_populates="stickers")  # Temporalmente comentado