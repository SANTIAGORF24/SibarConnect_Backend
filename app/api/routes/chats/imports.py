from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import tempfile
import os
from pathlib import Path
from fastapi.responses import FileResponse
from app.db.session import get_db
from app.services.whatsapp_import import import_whatsapp_chat
from app.services.companies import get_company

router = APIRouter()


@router.post("/import")
async def import_whatsapp_chat_endpoint(
    file: UploadFile = File(...),
    company_id: int = Form(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un ZIP exportado de WhatsApp")
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        result = await import_whatsapp_chat(temp_file_path, company_id, db)
        if result['success']:
            return {
                "success": True,
                "message": "Chat importado exitosamente",
                "data": {
                    "chat_id": result['chat_id'],
                    "messages_imported": result['messages_imported'],
                    "media_files_saved": result['media_files_saved']
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Error importando chat: {'; '.join(result['errors'])}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando importación: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.get("/media/{company_id}/{filename}")
def serve_media_file(company_id: int, filename: str):
    media_path = Path(f"media/company_{company_id}/whatsapp_imports/{filename}")
    if not media_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    allowed_dir = Path(f"media/company_{company_id}")
    try:
        media_path.resolve().relative_to(allowed_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acceso no autorizado al archivo")
    content_type = "application/octet-stream"
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        content_type = f"image/{filename.split('.')[-1]}"
    elif filename.lower().endswith(('.mp4', '.avi', '.mov')):
        content_type = f"video/{filename.split('.')[-1]}"
    elif filename.lower().endswith(('.mp3', '.wav', '.ogg')):
        content_type = f"audio/{filename.split('.')[-1]}"
    return FileResponse(path=str(media_path), media_type=content_type, filename=filename)


