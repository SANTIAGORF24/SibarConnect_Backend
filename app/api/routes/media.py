from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os

router = APIRouter()

@router.get("/media/company_{company_id}/whatsapp/chat_{chat_id}/{filename}")
async def serve_media_file(company_id: int, chat_id: int, filename: str):
    """
    Sirve archivos multimedia almacenados localmente
    """
    try:
        # Construir la ruta del archivo
        base_media_path = Path("media")
        file_path = base_media_path / f"company_{company_id}" / "whatsapp" / f"chat_{chat_id}" / filename
        
        # Verificar que el archivo existe
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Verificar que el archivo está dentro del directorio permitido (seguridad)
        if not str(file_path.resolve()).startswith(str(base_media_path.resolve())):
            raise HTTPException(status_code=403, detail="Acceso denegado")
        
        # Determinar el tipo de contenido basado en la extensión
        content_type = get_content_type(filename)
        
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sirviendo archivo: {str(e)}")


def get_content_type(filename: str) -> str:
    """Determina el tipo de contenido basado en la extensión del archivo"""
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'm4a': 'audio/mp4',
        'wav': 'audio/wav',
        'mp4': 'video/mp4',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo',
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'zip': 'application/zip',
        'txt': 'text/plain'
    }
    
    return content_types.get(extension, 'application/octet-stream')
