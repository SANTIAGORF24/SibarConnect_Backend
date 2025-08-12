#!/usr/bin/env python3
"""
Script de migración para agregar la columna attachment_url a la tabla messages
"""

import sqlite3
import os
from pathlib import Path

def add_attachment_url_column():
    """Agregar la columna attachment_url a la tabla messages"""
    
    # Obtener la ruta de la base de datos
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "data" / "app.db"
    
    if not db_path.exists():
        print(f"❌ Base de datos no encontrada en: {db_path}")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'attachment_url' in columns:
            print("✅ La columna 'attachment_url' ya existe en la tabla messages")
            return True
        
        # Agregar la columna
        cursor.execute("""
            ALTER TABLE messages 
            ADD COLUMN attachment_url VARCHAR(500)
        """)
        
        conn.commit()
        print("✅ Columna 'attachment_url' agregada exitosamente a la tabla messages")
        
        # Verificar que se agregó correctamente
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'attachment_url' in columns:
            print("✅ Migración completada exitosamente")
            return True
        else:
            print("❌ Error: La columna no se agregó correctamente")
            return False
            
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🔄 Iniciando migración de base de datos...")
    success = add_attachment_url_column()
    
    if success:
        print("🎉 Migración completada exitosamente")
    else:
        print("💥 Error en la migración")
