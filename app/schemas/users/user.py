from pydantic import BaseModel, EmailStr
from pydantic.config import ConfigDict
from typing import Optional
from app.schemas.roles.role import RoleOut


class CompanyInfo(BaseModel):
  """Información básica de empresa para el usuario"""
  id: int
  nombre: str
  razon_social: str
  nit: str
  email: str
  telefono: str | None = None
  direccion: str | None = None
  activa: bool


class UserBase(BaseModel):
  first_name: str
  last_name: str
  username: str
  email: EmailStr
  is_super_admin: bool = False


class UserCreate(UserBase):
  password: str
  role_id: int | None = None
  company_id: int | None = None


class UserLogin(BaseModel):
  email: EmailStr
  password: str


class UserOut(UserBase):
  id: int
  role: Optional[RoleOut] = None
  company_id: int | None = None
  company: Optional[CompanyInfo] = None

  model_config = ConfigDict(from_attributes=True)


