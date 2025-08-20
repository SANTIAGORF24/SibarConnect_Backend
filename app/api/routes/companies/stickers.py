from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import shutil
from pathlib import Path
import requests
from app.db.session import get_db
from app.models.companies.sticker import CompanySticker
from app.schemas.companies.sticker import CompanyStickerOut, CompanyStickerCreate

router = APIRouter()

@router.get("/{company_id}", response_model=List[CompanyStickerOut])
def get_company_stickers(
    company_id: int,
    db: Session = Depends(get_db)
):
    """Obtener todos los stickers de una empresa"""
    stickers = db.query(CompanySticker).filter(
        CompanySticker.company_id == company_id
    ).all()
    return stickers

@router.post("/save", response_model=CompanyStickerOut)
async def save_sticker_from_url(
    sticker_url: str = Form(...),
    sticker_name: str = Form(...),
    company_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Guardar un sticker desde una URL"""
    print(f"🔍 Debug - Recibiendo datos:")
    print(f"  - sticker_url: {sticker_url}")
    print(f"  - sticker_name: {sticker_name}")
    print(f"  - company_id: {company_id}")
    
    try:
        # Crear directorio para la empresa si no existe
        company_dir = Path(f"media/company_{company_id}/stickers")
        company_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Directorio creado: {company_dir}")
        
        # Generar nombre único para el archivo
        file_extension = ".webp"  # Default para stickers
        if "." in sticker_url:
            file_extension = "." + sticker_url.split(".")[-1].split("?")[0]
        
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = company_dir / unique_filename
        print(f"📄 Archivo destino: {file_path}")
        
        # Verificar si es una URL local del mismo servidor
        if sticker_url.startswith("http://localhost:8000/media/") or sticker_url.startswith("/media/"):
            # Es un archivo local, copiarlo directamente
            local_path = sticker_url.replace("http://localhost:8000", "").lstrip("/")
            source_file = Path(local_path)
            
            print(f"📋 Copiando archivo local desde: {source_file}")
            
            if source_file.exists():
                # Copiar el archivo
                with open(source_file, "rb") as src, open(file_path, "wb") as dst:
                    content = src.read()
                    dst.write(content)
                
                file_size = len(content)
                print(f"✅ Archivo copiado exitosamente, tamaño: {file_size} bytes")
                
                # Determinar mime type basado en extensión
                mime_type = "image/webp"
                if file_extension.lower() in ['.jpg', '.jpeg']:
                    mime_type = "image/jpeg"
                elif file_extension.lower() == '.png':
                    mime_type = "image/png"
                elif file_extension.lower() == '.gif':
                    mime_type = "image/gif"
                
            else:
                raise FileNotFoundError(f"Archivo fuente no encontrado: {source_file}")
                
        else:
            # Es una URL externa, descargar normalmente
            print(f"⬇️ Descargando desde: {sticker_url}")
            response = requests.get(sticker_url, timeout=30)
            response.raise_for_status()
            
            content = response.content
            file_size = len(content)
            mime_type = response.headers.get('content-type', 'image/webp')
            
            # Guardar el archivo
            with open(file_path, "wb") as f:
                f.write(content)
            
            print(f"✅ Descarga exitosa, tamaño: {file_size} bytes")
        
        print(f"💾 Archivo guardado en: {file_path}")
        
        # Crear URL relativa para servir el archivo
        relative_path = f"/media/company_{company_id}/stickers/{unique_filename}"
        print(f"🔗 URL relativa: {relative_path}")
        
        # Crear registro en la base de datos
        sticker_data = CompanyStickerCreate(
            company_id=company_id,
            name=sticker_name,
            file_path=str(file_path),
            url=relative_path,
            file_size=file_size,
            mime_type=mime_type
        )
        print(f"📊 Datos del sticker: {sticker_data}")
        
        db_sticker = CompanySticker(**sticker_data.dict())
        db.add(db_sticker)
        db.commit()
        db.refresh(db_sticker)
        print(f"✅ Sticker guardado en BD con ID: {db_sticker.id}")
        
        return db_sticker
        
    except FileNotFoundError as e:
        print(f"❌ Archivo no encontrado: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Archivo fuente no encontrado: {str(e)}")
    except requests.RequestException as e:
        print(f"❌ Error de descarga: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error descargando sticker: {str(e)}")
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error guardando sticker: {str(e)}")

@router.delete("/{sticker_id}")
def delete_sticker(
    sticker_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar un sticker"""
    sticker = db.query(CompanySticker).filter(
        CompanySticker.id == sticker_id,
        CompanySticker.company_id == company_id
    ).first()
    
    if not sticker:
        raise HTTPException(status_code=404, detail="Sticker no encontrado")
    
    try:
        # Eliminar archivo físico
        if os.path.exists(sticker.file_path):
            os.remove(sticker.file_path)
        
        # Eliminar registro de la base de datos
        db.delete(sticker)
        db.commit()
        
        return {"success": True, "message": "Sticker eliminado exitosamente"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando sticker: {str(e)}")