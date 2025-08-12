#!/usr/bin/env python3
"""
Migración para agregar campos de YCloud a la tabla companies
"""

import sqlite3
import os
import sys

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_ycloud_fields():
    """Agregar campos de YCloud a la tabla companies"""
    
    # Ruta a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'app.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Base de datos no encontrada en {db_path}")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(companies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrations = []
        
        # Agregar columnas si no existen
        if 'ycloud_api_key' not in columns:
            migrations.append("ALTER TABLE companies ADD COLUMN ycloud_api_key TEXT NULL")
            
        if 'ycloud_webhook_url' not in columns:
            migrations.append("ALTER TABLE companies ADD COLUMN ycloud_webhook_url TEXT NULL")
            
        if 'whatsapp_phone_number' not in columns:
            migrations.append("ALTER TABLE companies ADD COLUMN whatsapp_phone_number TEXT NULL")
        
        if not migrations:
            print("✅ Todas las columnas de YCloud ya existen en la base de datos")
            return True
        
        # Ejecutar migraciones
        for migration in migrations:
            print(f"🔄 Ejecutando: {migration}")
            cursor.execute(migration)
        
        # Confirmar cambios
        conn.commit()
        print(f"✅ Migración completada exitosamente. {len(migrations)} columnas agregadas.")
        
        # Verificar que las columnas se agregaron correctamente
        cursor.execute("PRAGMA table_info(companies)")
        new_columns = [row[1] for row in cursor.fetchall()]
        
        print("\n📋 Columnas actuales en la tabla companies:")
        for col in new_columns:
            print(f"   - {col}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error en la migración: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Iniciando migración de campos YCloud...")
    success = migrate_ycloud_fields()
    
    if success:
        print("\n🎉 Migración completada exitosamente!")
        print("Ahora puedes reiniciar el servidor backend.")
    else:
        print("\n💥 Migración falló. Revisa los errores arriba.")
        sys.exit(1)
