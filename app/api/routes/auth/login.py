from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.users.user import UserLogin, UserOut
from app.services.users import get_user_by_email
from app.models.roles.role import Role
from app.models.companies.company import Company
import json
from app.services.security import verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
  user = get_user_by_email(db, payload.email)
  if not user or not verify_password(payload.password, user.hashed_password):
    raise HTTPException(status_code=401, detail="Credenciales inválidas")
  
  # Enriquecer con rol y permisos
  role_data = None
  if getattr(user, "role_id", None):
    role = db.get(Role, user.role_id)
    if role:
      try:
        allowed_paths = json.loads(role.allowed_paths or "[]")
      except Exception:
        allowed_paths = []
      role_data = {
        "id": role.id,
        "name": role.name,
        "is_admin": role.is_admin,
        "allowed_paths": allowed_paths,
      }
  
  # Enriquecer con información de la empresa
  company_data = None
  if getattr(user, "company_id", None):
    company = db.get(Company, user.company_id)
    if company:
      company_data = {
        "id": company.id,
        "nombre": company.nombre,
        "razon_social": company.razon_social,
        "nit": company.nit,
        "email": company.email,
        "telefono": company.telefono,
        "direccion": company.direccion,
        "activa": company.activa,
      }
  
  out = {
    "id": user.id,
    "first_name": user.first_name,
    "last_name": user.last_name,
    "username": user.username,
    "email": user.email,
    "is_super_admin": user.is_super_admin,
    "role": role_data,
    "company_id": getattr(user, "company_id", None),
    "company": company_data,
  }
  return out


