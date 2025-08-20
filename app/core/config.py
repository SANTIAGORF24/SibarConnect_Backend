import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class Settings:
  app_name: str = os.getenv("APP_NAME", "SibarConnect API")
  api_prefix: str = os.getenv("API_PREFIX", "/api")
  server_url: str = os.getenv("SERVER_URL", "http://localhost:8000")
  # URL pública para recursos (usar ngrok cuando esté disponible)
  public_url: str = os.getenv("PUBLIC_URL", "https://d79757fc9d41.ngrok-free.app")
  deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
  gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")

  # Usar ruta absoluta para la base de datos
  @property
  def sqlite_path(self) -> str:
    if os.getenv("SQLITE_PATH"):
      return os.getenv("SQLITE_PATH")
    
    # Ruta absoluta al archivo de base de datos en el directorio backend/data
    backend_dir = Path(__file__).parent.parent.parent  # backend/
    db_path = backend_dir / "data" / "app.db"
    return str(db_path)

  admin_email: str | None = os.getenv("ADMIN_EMAIL")
  admin_password: str | None = os.getenv("ADMIN_PASSWORD")


settings = Settings()


