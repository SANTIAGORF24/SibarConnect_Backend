from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from .core.config import settings
from .db.session import Base, engine
from . import models  # noqa: F401
from .api.routes.auth.login import router as auth_router
from .api.routes.users.users import router as users_router
from .api.routes.roles.roles import router as roles_router
from .api.routes.companies.companies import router as companies_router
from .api.routes.companies.stickers import router as stickers_router
from .api.routes.webhooks.ycloud import router as webhooks_router
from .api.routes.chats.chats import router as chats_router
from .api.routes.media import router as media_router
from sqlalchemy import text


def create_app() -> FastAPI:
  Base.metadata.create_all(bind=engine)
  with engine.begin() as conn:
    try:
      # Verificar y agregar columnas para users
      info = conn.exec_driver_sql("PRAGMA table_info('users')").fetchall()
      cols = [row[1] for row in info]
      if 'role_id' not in cols:
        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN role_id INTEGER")
      if 'company_id' not in cols:
        conn.exec_driver_sql("ALTER TABLE users ADD COLUMN company_id INTEGER")
      
      # Verificar y agregar columnas para companies (YCloud)
      info = conn.exec_driver_sql("PRAGMA table_info('companies')").fetchall()
      cols = [row[1] for row in info]
      if 'ycloud_api_key' not in cols:
        conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN ycloud_api_key TEXT")
      if 'ycloud_webhook_url' not in cols:
        conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN ycloud_webhook_url TEXT")
      if 'whatsapp_phone_number' not in cols:
        conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN whatsapp_phone_number TEXT")
      
      # Verificar y crear tablas de chats si no existen
      try:
        conn.exec_driver_sql("SELECT 1 FROM chats LIMIT 1")
      except Exception:
        # La tabla no existe, crearla
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            phone_number VARCHAR(20) NOT NULL,
            customer_name VARCHAR(100),
            last_message_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
          )
        """)
        
      try:
        conn.exec_driver_sql("SELECT 1 FROM messages LIMIT 1")
      except Exception:
        # La tabla no existe, crearla
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            content TEXT,
            message_type VARCHAR(20) DEFAULT 'text',
            direction VARCHAR(10) NOT NULL,
            user_id INTEGER,
            whatsapp_message_id VARCHAR(100),
            wamid VARCHAR(100),
            sender_name VARCHAR(100),
            status VARCHAR(20) DEFAULT 'sent',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
          )
        """)
        
      # Verificar y crear tabla de stickers si no existe
      try:
        conn.exec_driver_sql("SELECT 1 FROM company_stickers LIMIT 1")
      except Exception:
        # La tabla no existe, crearla
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS company_stickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_url VARCHAR(500) NOT NULL,
            mime_type VARCHAR(100),
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
          )
        """)
        
    except Exception:
      pass

  app = FastAPI(title=settings.app_name)

  # Endpoint específico para archivos webp con tipo MIME correcto (ANTES del mount)
  @app.get("/media/{company_id}/stickers/{filename}")
  async def serve_sticker(company_id: str, filename: str):
    media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "media")
    file_path = os.path.join(media_dir, company_id, "stickers", filename)
    
    if os.path.exists(file_path) and filename.endswith('.webp'):
      return FileResponse(file_path, media_type="image/webp")
    else:
      from fastapi import HTTPException
      raise HTTPException(status_code=404, detail="File not found")

  # Configurar archivos estáticos para multimedia (otros archivos)
  # La carpeta media está en la raíz del proyecto (un nivel arriba del directorio backend)
  media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "media")
  if not os.path.exists(media_dir):
    os.makedirs(media_dir, exist_ok=True)
  
  app.mount("/media", StaticFiles(directory=media_dir), name="media")

  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  app.include_router(auth_router, prefix=settings.api_prefix)
  app.include_router(users_router, prefix=settings.api_prefix)
  app.include_router(companies_router, prefix=settings.api_prefix)
  app.include_router(roles_router, prefix=settings.api_prefix)
  app.include_router(chats_router, prefix=f"{settings.api_prefix}/chats")
  app.include_router(stickers_router, prefix=f"{settings.api_prefix}/chats/stickers")
  app.include_router(webhooks_router, prefix=f"{settings.api_prefix}/webhooks")
  app.include_router(media_router, prefix=settings.api_prefix)

  return app


app = create_app()


