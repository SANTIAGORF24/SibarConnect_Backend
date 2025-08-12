import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.roles.role import RoleCreate, RoleOut, RoleUpdate
from app.services.roles import list_roles, create_role, get_role, update_role, delete_role


router = APIRouter(prefix="/roles", tags=["roles"])


def _serialize_role(role) -> RoleOut:
  try:
    allowed_paths = json.loads(role.allowed_paths or "[]")
  except Exception:
    allowed_paths = []
  return RoleOut.model_validate({
    "id": role.id,
    "name": role.name,
    "is_admin": role.is_admin,
    "allowed_paths": allowed_paths,
  })


@router.get("", response_model=list[RoleOut])
def list_(db: Session = Depends(get_db)):
  return [_serialize_role(r) for r in list_roles(db)]


@router.post("", response_model=RoleOut)
def create(payload: RoleCreate, db: Session = Depends(get_db)):
  try:
    role = create_role(db, payload)
    return _serialize_role(role)
  except ValueError as e:
    raise HTTPException(status_code=409, detail=str(e))


@router.get("/{role_id}", response_model=RoleOut)
def get(role_id: int, db: Session = Depends(get_db)):
  role = get_role(db, role_id)
  if not role:
    raise HTTPException(status_code=404, detail="Rol no encontrado")
  return _serialize_role(role)


@router.put("/{role_id}", response_model=RoleOut)
def update(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db)):
  try:
    role = update_role(db, role_id, payload)
  except ValueError as e:
    raise HTTPException(status_code=409, detail=str(e))
  if not role:
    raise HTTPException(status_code=404, detail="Rol no encontrado")
  return _serialize_role(role)


@router.delete("/{role_id}")
def delete(role_id: int, db: Session = Depends(get_db)):
  ok = delete_role(db, role_id)
  if not ok:
    raise HTTPException(status_code=404, detail="Rol no encontrado")
  return {"ok": True}


