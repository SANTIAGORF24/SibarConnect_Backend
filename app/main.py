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
from .api.routes.chats import router as chats_router
from .api.routes.media import router as media_router
from .api.routes.templates.templates import router as templates_router
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
      # Asegurar columnas nuevas en chats
      try:
        info = conn.exec_driver_sql("PRAGMA table_info('chats')").fetchall()
        cols = [row[1] for row in info]
        if 'priority' not in cols:
          conn.exec_driver_sql("ALTER TABLE chats ADD COLUMN priority VARCHAR(10) DEFAULT 'low'")
      except Exception:
        pass
        
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

      # Tabla de resúmenes
      try:
        conn.exec_driver_sql("SELECT 1 FROM chat_summaries LIMIT 1")
      except Exception:
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS chat_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            interest VARCHAR(20) DEFAULT 'Indeciso',
            provider VARCHAR(50) DEFAULT 'gemini',
            model VARCHAR(50) DEFAULT 'gemini-2.5-flash',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (chat_id) REFERENCES chats (id),
            FOREIGN KEY (company_id) REFERENCES companies (id)
          )
        """)
      # Asegurar columna 'interest' por si existía estructura previa
      try:
        info = conn.exec_driver_sql("PRAGMA table_info('chat_summaries')").fetchall()
        cols = [row[1] for row in info]
        if 'interest' not in cols:
          conn.exec_driver_sql("ALTER TABLE chat_summaries ADD COLUMN interest VARCHAR(20) DEFAULT 'Indeciso'")
        if 'provider' not in cols:
          conn.exec_driver_sql("ALTER TABLE chat_summaries ADD COLUMN provider VARCHAR(50) DEFAULT 'gemini'")
        if 'model' not in cols:
          conn.exec_driver_sql("ALTER TABLE chat_summaries ADD COLUMN model VARCHAR(50) DEFAULT 'gemini-2.5-flash'")
        if 'updated_at' not in cols:
          conn.exec_driver_sql("ALTER TABLE chat_summaries ADD COLUMN updated_at TIMESTAMP")
      except Exception:
        pass

      # Tabla de citas
      try:
        conn.exec_driver_sql("SELECT 1 FROM appointments LIMIT 1")
      except Exception:
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            assigned_user_id INTEGER NOT NULL,
            start_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id),
            FOREIGN KEY (chat_id) REFERENCES chats (id),
            FOREIGN KEY (assigned_user_id) REFERENCES users (id),
            UNIQUE (assigned_user_id, start_at)
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
      # Verificar y crear tablas de templates si no existen
      try:
        conn.exec_driver_sql("SELECT 1 FROM templates LIMIT 1")
      except Exception:
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
          )
        """)
      try:
        conn.exec_driver_sql("SELECT 1 FROM template_items LIMIT 1")
      except Exception:
        conn.exec_driver_sql("""
          CREATE TABLE IF NOT EXISTS template_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0,
            item_type VARCHAR(20) NOT NULL,
            text_content TEXT,
            media_url VARCHAR(500),
            mime_type VARCHAR(100),
            caption VARCHAR(500),
            FOREIGN KEY (template_id) REFERENCES templates (id)
          )
        """)
        
    except Exception:
      pass

  app = FastAPI(
    title=settings.app_name,
    openapi_tags=[
      {"name": "Auth", "description": "Autenticación y sesiones"},
      {"name": "Users", "description": "Gestión de usuarios"},
      {"name": "Companies", "description": "Gestión de empresas"},
      {"name": "Roles", "description": "Roles y permisos"},
      {"name": "Chats", "description": "Operaciones de chats, mensajes y adjuntos"},
      {"name": "Stickers", "description": "Gestión de stickers de empresa"},
      {"name": "Webhooks", "description": "Webhooks de integración (YCloud)"},
      {"name": "Media", "description": "Servir archivos multimedia"},
      {"name": "Templates", "description": "Plantillas de contenido"},
    ]
  )

  # Endpoint específico para archivos webp con tipo MIME correcto (ANTES del mount)
  @app.get("/media/{company_id}/stickers/{filename}", tags=["Media"])
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  app.include_router(auth_router, prefix=settings.api_prefix, tags=["Auth"])
  app.include_router(users_router, prefix=settings.api_prefix, tags=["Users"])
  app.include_router(companies_router, prefix=settings.api_prefix, tags=["Companies"])
  app.include_router(roles_router, prefix=settings.api_prefix, tags=["Roles"])
  app.include_router(chats_router, prefix=f"{settings.api_prefix}/chats", tags=["Chats"])
  app.include_router(stickers_router, prefix=f"{settings.api_prefix}/chats/stickers", tags=["Stickers"])
  app.include_router(webhooks_router, prefix=f"{settings.api_prefix}/webhooks", tags=["Webhooks"])
  app.include_router(media_router, prefix=settings.api_prefix, tags=["Media"])
  app.include_router(templates_router, prefix=f"{settings.api_prefix}/templates", tags=["Templates"])

  return app


app = create_app()


