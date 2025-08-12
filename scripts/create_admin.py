import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
  sys.path.insert(0, str(BACKEND_ROOT))

try:
  from app.db.session import SessionLocal, engine, Base
  from app.models.users.user import User
  from app.services.security import hash_password
except ModuleNotFoundError:
  if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
  from backend.app.db.session import SessionLocal, engine, Base
  from backend.app.models.users.user import User
  from backend.app.services.security import hash_password


def main():
  Base.metadata.create_all(bind=engine)
  db = SessionLocal()
  try:
    email = os.getenv("ADMIN_EMAIL", "admin@admin.com")
    username = os.getenv("ADMIN_USERNAME", "admin")
    first_name = os.getenv("ADMIN_FIRST_NAME", "Admin")
    last_name = os.getenv("ADMIN_LAST_NAME", "User")
    password = os.getenv("ADMIN_PASSWORD", "admin123")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
      user = User(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hash_password(password),
        is_super_admin=True,
      )
      db.add(user)
      db.commit()
      db.refresh(user)
      print(f"Admin creado: {user.email}")
    else:
      print("Admin ya existe; no se realizaron cambios")
  finally:
    db.close()


if __name__ == "__main__":
  main()


