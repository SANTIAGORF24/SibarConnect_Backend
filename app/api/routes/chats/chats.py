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


@router.post("/send-file")
async def send_file_message(
    company_id: int,
    user_id: int,
    chat_id: int = Form(...),
    file: UploadFile = File(...),
    caption: str = Form(""),
    db: Session = Depends(get_db)
):
    """Enviar un archivo como mensaje de WhatsApp"""
    
    print(f"🔍 Debug send-file iniciado:")
    print(f"  - file.filename: {file.filename}")
    print(f"  - company_id: {company_id}")
    print(f"  - user_id: {user_id}")
    print(f"  - chat_id: {chat_id}")
    print(f"  - caption: {caption}")
    
    # Obtener el chat y verificar que pertenece a la empresa
    chat = get_chat_by_id(db, chat_id, company_id)
    print(f"  - chat encontrado: {chat.phone_number if chat else 'No encontrado'}")
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
        # Validaciones de archivo antes de procesarlo
        file_extension = Path(file.filename).suffix.lower() if file.filename else ""
        print(f"  - file_extension: {file_extension}")
        
        # Leer el contenido del archivo una vez
        content = await file.read()
        file_size = len(content)
        print(f"  - file_size: {file_size:,} bytes")
        
        # Validar tamaño según el tipo de archivo
        if file_extension in ['.mp4', '.mov', '.avi']:
            # Videos: máximo 16MB
            if file_size > 16 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"El video es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 16MB"
                )
        elif file_extension in ['.jpg', '.jpeg', '.png', '.webp']:
            # Imágenes: máximo 5MB
            if file_size > 5 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"La imagen es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 5MB"
                )
        elif file_extension in ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.amr']:
            # Audios: máximo 16MB
            if file_size > 16 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"El audio es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 16MB"
                )
        else:
            # Documentos: máximo 100MB
            if file_size > 100 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"El documento es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 100MB"
                )
        
        # Verificar si es un archivo WAV que necesita conversión
        if file_extension == '.wav':
            print(f"⚠️ Archivo WAV detectado, necesita conversión a MP3")
            # Por ahora rechazamos WAV hasta implementar conversión
            raise HTTPException(
                status_code=400,
                detail="Los archivos WAV no son compatibles con WhatsApp. Por favor, convierta el audio a formato MP3, OGG, M4A, AAC o AMR antes de enviarlo."
            )
        
        # Crear directorio para la empresa si no existe
        company_dir = Path(f"media/company_{company_id}/uploads")
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre único para el archivo
        import uuid
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = company_dir / unique_filename
        
        # Guardar el archivo
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Determinar el tipo de mensaje basado en la extensión del archivo
        if file_extension in ['.jpg', '.jpeg', '.png', '.webp']:
            message_type = 'image'
        elif file_extension in ['.mp4', '.mov', '.avi']:
            message_type = 'video'
        elif file_extension in ['.mp3', '.ogg', '.m4a', '.aac', '.amr', '.wav']:
            message_type = 'audio'
        else:
            message_type = 'document'
        
        # Construir URL del archivo
        file_url = f"/media/company_{company_id}/uploads/{unique_filename}"
        
        print(f"🔍 Debug send-file:")
        print(f"  - Archivo guardado: {file_path}")
        print(f"  - URL relativa: {file_url}")
        print(f"  - Tipo de mensaje: {message_type}")
        
        # Enviar archivo a través de YCloud
        try:
            ycloud_service = create_ycloud_service(company.ycloud_api_key)
            # Para archivos, YCloud necesita la URL completa
            from app.core.config import settings
            full_file_url = f"{settings.public_url}{file_url}"
            
            print(f"  - URL completa: {full_file_url}")
            print(f"  - Enviando a: {chat.phone_number}")
            
            result = await ycloud_service.send_message(
                to=chat.phone_number,
                message=full_file_url,
                from_number=company.whatsapp_phone_number,
                message_type=message_type
            )
            
            print(f"  - Resultado YCloud: {result}")
            
        except Exception as ycloud_error:
            print(f"❌ Error en YCloud: {ycloud_error}")
            # Si falla el envío, eliminar el archivo guardado
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Error enviando a WhatsApp: {str(ycloud_error)}"
            )
        
        if result.get("success"):
            # Guardar el mensaje en la base de datos
            message_data = MessageCreate(
                chat_id=chat_id,
                content=caption if caption else f"Archivo: {file.filename}",
                message_type=message_type,
                direction="outgoing",
                user_id=user_id,
                whatsapp_message_id=result.get("message_id"),
                sender_name="Agente",
                attachment_url=file_url
            )
            
            message = create_message(db, message_data)
            
            return {
                "success": True,
                "message": "Archivo enviado correctamente",
                "message_id": message.id,
                "whatsapp_message_id": result.get("message_id"),
                "file_url": file_url
            }
        else:
            # Si falla el envío, eliminar el archivo guardado
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"Error al enviar archivo: {result.get('error', 'Error desconocido')}"
            )
            
    except HTTPException:
        # Re-lanzar HTTPExceptions para que mantengan su status code original
        raise
    except Exception as e:
        print(f"❌ Error en send_file_message:")
        print(f"  - Error: {str(e)}")
        print(f"  - Tipo: {type(e).__name__}")
        import traceback
        print(f"  - Traceback: {traceback.format_exc()}")
        
        # Si hay error, eliminar el archivo si se guardó
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
            print(f"  - Archivo eliminado: {file_path}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al enviar archivo: {str(e)}"
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
