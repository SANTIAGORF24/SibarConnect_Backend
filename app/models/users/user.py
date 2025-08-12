from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class User(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(primary_key=True, index=True)
  first_name: Mapped[str] = mapped_column(String(120))
  last_name: Mapped[str] = mapped_column(String(120))
  username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
  email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
  hashed_password: Mapped[str] = mapped_column(String(255))
  is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
  role_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("roles.id"), nullable=True)
  company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("companies.id"), nullable=True)


