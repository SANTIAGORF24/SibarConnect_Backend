from pydantic import BaseModel, EmailStr, Field
from pydantic.config import ConfigDict
from datetime import datetime


class CompanyBase(BaseModel):
  nombre: str
  razon_social: str
  nit: str = Field(min_length=5)
  responsable: str
  activa: bool = True
  cantidad_usuarios: int = 0
  email: EmailStr
  telefono: str | None = None
  direccion: str | None = None
  ycloud_api_key: str | None = None
  ycloud_webhook_url: str | None = None
  whatsapp_phone_number: str | None = None


class YCloudConfig(BaseModel):
  api_key: str
  webhook_url: str | None = None
  phone_number: str | None = None


class YCloudTestResult(BaseModel):
  success: bool
  message: str
  phone_number: str | None = None
  webhook_status: str | None = None


class CompanyCreate(CompanyBase):
  pass


class CompanyUpdate(BaseModel):
  nombre: str | None = None
  razon_social: str | None = None
  nit: str | None = None
  responsable: str | None = None
  activa: bool | None = None
  cantidad_usuarios: int | None = None
  email: EmailStr | None = None
  telefono: str | None = None
  direccion: str | None = None


class CompanyOut(CompanyBase):
  id: int
  created_at: datetime

  model_config = ConfigDict(from_attributes=True)


