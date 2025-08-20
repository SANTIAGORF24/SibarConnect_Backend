from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pathlib import Path
from app.db.session import get_db
from app.services.chats import (
    get_chat_by_id,
    get_messages_by_chat,
    create_message,
)
from app.services.companies import get_company
from app.services.ycloud import create_ycloud_service
from app.schemas.chats.chat import (
    MessageOut,
    SendMessageRequest,
    MessageCreate,
)

router = APIRouter()


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def get_chat_messages(
    chat_id: int,
    company_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
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
    chat = get_chat_by_id(db, request.chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key:
        raise HTTPException(status_code=400, detail="La empresa no tiene configurada la API de YCloud")
    if not company.whatsapp_phone_number:
        raise HTTPException(status_code=400, detail="La empresa no tiene configurado un número de WhatsApp")
    try:
        ycloud_service = create_ycloud_service(company.ycloud_api_key)
        result = await ycloud_service.send_message(
            to=chat.phone_number,
            message=request.content,
            from_number=company.whatsapp_phone_number,
            message_type=request.message_type
        )
        if result.get("success"):
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
            raise HTTPException(status_code=400, detail=f"Error al enviar mensaje: {result.get('error', 'Error desconocido')}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al enviar mensaje: {str(e)}")


@router.post("/send-file")
async def send_file_message(
    company_id: int,
    user_id: int,
    chat_id: int = Form(...),
    file: UploadFile = File(...),
    caption: str = Form(""),
    db: Session = Depends(get_db)
):
    chat = get_chat_by_id(db, chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key:
        raise HTTPException(status_code=400, detail="La empresa no tiene configurada la API de YCloud")
    if not company.whatsapp_phone_number:
        raise HTTPException(status_code=400, detail="La empresa no tiene configurado un número de WhatsApp")
    try:
        file_extension = Path(file.filename).suffix.lower() if file.filename else ""
        content = await file.read()
        file_size = len(content)
        if file_extension in ['.mp4', '.mov', '.avi']:
            if file_size > 16 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"El video es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 16MB")
        elif file_extension in ['.jpg', '.jpeg', '.png', '.webp']:
            if file_size > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"La imagen es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 5MB")
        elif file_extension in ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.amr']:
            if file_size > 16 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"El audio es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 16MB")
        else:
            if file_size > 100 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"El documento es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 100MB")
        if file_extension == '.wav':
            raise HTTPException(status_code=400, detail="Los archivos WAV no son compatibles con WhatsApp. Por favor, convierta el audio a formato MP3, OGG, M4A, AAC o AMR antes de enviarlo.")
        from uuid import uuid4
        company_dir = Path(f"media/company_{company_id}/uploads")
        company_dir.mkdir(parents=True, exist_ok=True)
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = company_dir / unique_filename
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        if file_extension in ['.jpg', '.jpeg', '.png', '.webp']:
            message_type = 'image'
        elif file_extension in ['.mp4', '.mov', '.avi']:
            message_type = 'video'
        elif file_extension in ['.mp3', '.ogg', '.m4a', '.aac', '.amr', '.wav']:
            message_type = 'audio'
        else:
            message_type = 'document'
        file_url = f"/media/company_{company_id}/uploads/{unique_filename}"
        try:
            from app.core.config import settings
            ycloud_service = create_ycloud_service(company.ycloud_api_key)
            full_file_url = f"{settings.public_url}{file_url}"
            result = await ycloud_service.send_message(
                to=chat.phone_number,
                message=full_file_url,
                from_number=company.whatsapp_phone_number,
                message_type=message_type,
                caption=caption if caption else None
            )
        except Exception as ycloud_error:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Error enviando a WhatsApp: {str(ycloud_error)}")
        if result.get("success"):
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
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail=f"Error al enviar archivo: {result.get('error', 'Error desconocido')}")
    except HTTPException:
        raise
    except Exception as e:
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error interno al enviar archivo: {str(e)}")


