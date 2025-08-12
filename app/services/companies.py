from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.companies.company import Company
from app.schemas.companies.company import CompanyCreate, CompanyUpdate, YCloudConfig


def list_companies(db: Session) -> list[Company]:
  return list(db.scalars(select(Company).order_by(Company.created_at.desc())))


def create_company(db: Session, payload: CompanyCreate) -> Company:
  company = Company(
    nombre=payload.nombre,
    razon_social=payload.razon_social,
    nit=payload.nit,
    responsable=payload.responsable,
    activa=payload.activa,
    cantidad_usuarios=payload.cantidad_usuarios,
    email=payload.email,
    telefono=payload.telefono or "",
    direccion=payload.direccion or "",
  )
  db.add(company)
  db.commit()
  db.refresh(company)
  return company


def get_company(db: Session, company_id: int) -> Company | None:
  return db.get(Company, company_id)


def update_company(db: Session, company_id: int, payload: CompanyUpdate) -> Company | None:
  company = db.get(Company, company_id)
  if not company:
    return None
  for field, value in payload.model_dump(exclude_unset=True).items():
    setattr(company, field, value)
  db.commit()
  db.refresh(company)
  return company


def delete_company(db: Session, company_id: int) -> bool:
  company = db.get(Company, company_id)
  if not company:
    return False
  db.delete(company)
  db.commit()
  return True


def update_ycloud_config(db: Session, company_id: int, config: YCloudConfig) -> Company | None:
    """Actualizar la configuración de YCloud para una empresa"""
    company = db.get(Company, company_id)
    if not company:
        return None
    
    # Actualizar los campos de YCloud
    if config.api_key is not None:
        company.ycloud_api_key = config.api_key
    if config.phone_number is not None:
        company.whatsapp_phone_number = config.phone_number
    if config.webhook_url is not None:
        company.ycloud_webhook_url = config.webhook_url
    
    db.commit()
    db.refresh(company)
    return company


