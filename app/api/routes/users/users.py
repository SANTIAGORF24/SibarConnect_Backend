from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.users.user import UserCreate, UserOut
from app.services.users import create_user, list_users, update_user, delete_user


router = APIRouter(prefix="/users", tags=["users"])
@router.get("", response_model=list[UserOut])
def list_(db: Session = Depends(get_db)):
  return list_users(db)



@router.post("", response_model=UserOut)
def create(user_in: UserCreate, db: Session = Depends(get_db)):
  user = create_user(db, user_in)
  return user


@router.put("/{user_id}", response_model=UserOut)
def update(user_id: int, data: dict, db: Session = Depends(get_db)):
  user = update_user(db, user_id, data)
  if not user:
    raise HTTPException(status_code=404, detail="Usuario no encontrado")
  return user


@router.delete("/{user_id}")
def delete(user_id: int, db: Session = Depends(get_db)):
  ok = delete_user(db, user_id)
  if not ok:
    raise HTTPException(status_code=404, detail="Usuario no encontrado")
  return {"ok": True}


