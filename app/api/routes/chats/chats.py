from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import tempfile
import os
from pathlib import Path
from app.db.session import get_db
from app.services.chats import (
    get_chats_by_company,
    get_chat_by_id,
    get_messages_by_chat,
    create_message
)
from app.schemas.chats.chat import (
    ChatWithLastMessage,
    ChatOut,
    MessageOut,
    SendMessageRequest,
    MessageCreate
)
from app.services.ycloud import create_ycloud_service
from app.services.companies import get_company
from app.services.whatsapp_import import import_whatsapp_chat

router = APIRouter()


@router.get("/", response_model=List[ChatWithLastMessage])
def get_company_chats(
    company_id: int,
    db: Session = Depends(get_db)
):
    """Obtener todos los chats de una empresa"""
    chats = get_chats_by_company(db, company_id)
    return chats


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(
    chat_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """Obtener un chat específico con todos sus mensajes"""
    chat = get_chat_by_id(db, chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    return ChatOut.from_orm(chat)


@router.get("/{chat_id}/messages", response_model=List[MessageOut])
def get_chat_messages(
    chat_id: int,
    company_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Obtener mensajes de un chat específico"""
    # Verificar que el chat pertenece a la empresa
    chat = get_chat_by_id(db, chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    messages = get_messages_by_chat(db, chat_id, limit)
    return [MessageOut.from_orm(msg) for msg in messages]


@router.post("/send-message")
async def send_whatsapp_message(
    request: SendMessageRequest,
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Enviar un mensaje de WhatsApp"""
    
    # Obtener el chat y verificar que pertenece a la empresa
    chat = get_chat_by_id(db, request.chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    # Obtener la configuración de YCloud de la empresa
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key:
        raise HTTPException(
            status_code=400, 
            detail="La empresa no tiene configurada la API de YCloud"
        )
    
    if not company.whatsapp_phone_number:
        raise HTTPException(
            status_code=400, 
            detail="La empresa no tiene configurado un número de WhatsApp"
        )
    
    try:
        # Enviar mensaje a través de YCloud
        ycloud_service = create_ycloud_service(company.ycloud_api_key)
        result = await ycloud_service.send_message(
            to=chat.phone_number,
            message=request.content,
            from_number=company.whatsapp_phone_number,
            message_type=request.message_type
        )
        
        if result.get("success"):
            # Guardar el mensaje en la base de datos
            message_data = MessageCreate(
                chat_id=request.chat_id,
                content=request.content,
                message_type=request.message_type,
                direction="outgoing",
                user_id=user_id,
                whatsapp_message_id=result.get("message_id"),
                sender_name="Agente"
            )
            
            message = create_message(db, message_data)
            
            return {
                "success": True,
                "message": "Mensaje enviado correctamente",
                "message_id": message.id,
                "whatsapp_message_id": result.get("message_id")
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Error al enviar mensaje: {result.get('error', 'Error desconocido')}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al enviar mensaje: {str(e)}"
        )


@router.post("/import")
async def import_whatsapp_chat_endpoint(
    file: UploadFile = File(...),
    company_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    Importar un chat de WhatsApp desde un archivo ZIP exportado
    """
    # Verificar que el archivo sea un ZIP
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un ZIP exportado de WhatsApp"
        )
    
    # Verificar que la empresa existe
    company = get_company(db, company_id)
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Empresa no encontrada"
        )
    
    # Crear archivo temporal
    temp_file_path = None
    try:
        # Guardar el archivo subido temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Procesar la importación
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
            raise HTTPException(
                status_code=400,
                detail=f"Error importando chat: {'; '.join(result['errors'])}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando importación: {str(e)}"
        )
    
    finally:
        # Limpiar archivo temporal
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.get("/media/{company_id}/{filename}")
def serve_media_file(company_id: int, filename: str):
    """
    Servir archivos multimedia de chats importados
    """
    # Construir la ruta del archivo
    media_path = Path(f"media/company_{company_id}/whatsapp_imports/{filename}")
    
    # Verificar que el archivo existe
    if not media_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado"
        )
    
    # Verificar que está dentro del directorio permitido (seguridad)
    allowed_dir = Path(f"media/company_{company_id}")
    try:
        media_path.resolve().relative_to(allowed_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Acceso no autorizado al archivo"
        )
    
    # Determinar el tipo de contenido
    content_type = "application/octet-stream"
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        content_type = f"image/{filename.split('.')[-1]}"
    elif filename.lower().endswith(('.mp4', '.avi', '.mov')):
        content_type = f"video/{filename.split('.')[-1]}"
    elif filename.lower().endswith(('.mp3', '.wav', '.ogg')):
        content_type = f"audio/{filename.split('.')[-1]}"
    
    return FileResponse(
        path=str(media_path),
        media_type=content_type,
        filename=filename
    )


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    """
    Eliminar un chat y todos sus mensajes
    """
    from app.models.chats.chat import Chat, Message
    
    # Verificar que el chat existe y pertenece a la empresa
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.company_id == company_id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat no encontrado"
        )
    
    try:
        # Eliminar todos los mensajes del chat
        db.query(Message).filter(Message.chat_id == chat_id).delete()
        
        # Eliminar el chat
        db.query(Chat).filter(Chat.id == chat_id).delete()
        
        db.commit()
        
        return {"success": True, "message": "Chat eliminado exitosamente"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando chat: {str(e)}"
        )
