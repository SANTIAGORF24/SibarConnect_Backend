from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Role(Base):
  __tablename__ = "roles"

  id: Mapped[int] = mapped_column(primary_key=True, index=True)
  name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
  is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
  allowed_paths: Mapped[str] = mapped_column(Text, default="[]")


