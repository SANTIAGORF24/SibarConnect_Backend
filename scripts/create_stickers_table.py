"""
Script para crear la tabla de stickers de empresa
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def create_company_stickers_table():
    """Crear la tabla de stickers de empresa"""
    
    database_url = f"sqlite:///{settings.sqlite_path}"
    engine = create_engine(database_url)
    
    # SQL para crear la tabla
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS company_stickers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        url VARCHAR(500) NOT NULL,
        file_size INTEGER,
        mime_type VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id)
    );
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(create_table_sql))
            connection.commit()
            print("✅ Tabla company_stickers creada exitosamente")
    except Exception as e:
        print(f"❌ Error creando tabla: {e}")

if __name__ == "__main__":
    create_company_stickers_table()
