from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.users.user import User
from app.schemas.users.user import UserCreate
from app.services.security import hash_password
from app.models.roles.role import Role


def get_user_by_email(db: Session, email: str) -> User | None:
  return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, user_in: UserCreate) -> User:
  user = User(
    first_name=user_in.first_name,
    last_name=user_in.last_name,
    username=user_in.username,
    email=user_in.email,
    hashed_password=hash_password(user_in.password),
    is_super_admin=user_in.is_super_admin,
    role_id=user_in.role_id,
    company_id=user_in.company_id,
  )
  db.add(user)
  db.commit()
  db.refresh(user)
  return user


def list_users(db: Session) -> list[User]:
  return list(db.scalars(select(User).order_by(User.id)))


def update_user(db: Session, user_id: int, data: dict) -> User | None:
  user = db.get(User, user_id)
  if not user:
    return None
  if "password" in data:
    data["hashed_password"] = hash_password(data.pop("password"))
  for key, value in data.items():
    if hasattr(user, key):
      setattr(user, key, value)
  db.commit()
  db.refresh(user)
  return user


def delete_user(db: Session, user_id: int) -> bool:
  user = db.get(User, user_id)
  if not user:
    return False
  db.delete(user)
  db.commit()
  return True


