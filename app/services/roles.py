import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.roles.role import Role
from app.schemas.roles.role import RoleCreate, RoleUpdate


def list_roles(db: Session) -> list[Role]:
  return list(db.scalars(select(Role).order_by(Role.name)))


def get_role_by_name(db: Session, name: str) -> Role | None:
  return db.scalar(select(Role).where(Role.name == name))


def create_role(db: Session, payload: RoleCreate) -> Role:
  existing = db.scalar(select(Role).where(Role.name == payload.name))
  if existing:
    raise ValueError("Ya existe un rol con ese nombre")
  role = Role(
    name=payload.name,
    is_admin=payload.is_admin,
    allowed_paths=json.dumps(payload.allowed_paths or []),
  )
  db.add(role)
  db.commit()
  db.refresh(role)
  return role


def get_role(db: Session, role_id: int) -> Role | None:
  return db.get(Role, role_id)


def update_role(db: Session, role_id: int, payload: RoleUpdate) -> Role | None:
  role = db.get(Role, role_id)
  if not role:
    return None
  data = payload.model_dump(exclude_unset=True)
  if "name" in data and data["name"] is not None:
    existing = db.scalar(select(Role).where(Role.name == data["name"], Role.id != role_id))
    if existing:
      raise ValueError("Ya existe un rol con ese nombre")
  if "allowed_paths" in data and data["allowed_paths"] is not None:
    role.allowed_paths = json.dumps(data.pop("allowed_paths"))
  for field, value in data.items():
    setattr(role, field, value)
  db.commit()
  db.refresh(role)
  return role


def delete_role(db: Session, role_id: int) -> bool:
  role = db.get(Role, role_id)
  if not role:
    return False
  db.delete(role)
  db.commit()
  return True


