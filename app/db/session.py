from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
import os


class Base(DeclarativeBase):
  pass


db_dir = os.path.dirname(settings.sqlite_path)
os.makedirs(db_dir, exist_ok=True)

engine = create_engine(f"sqlite:///{settings.sqlite_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


