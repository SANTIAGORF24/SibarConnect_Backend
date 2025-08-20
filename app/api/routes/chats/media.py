from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.services.ycloud import create_ycloud_service
from app.services.companies import get_company
from app.services.chats import get_chat_by_id, create_message
from app.schemas.chats.chat import MessageCreate
from app.core.config import settings

router = APIRouter()


class SendMediaLinkPayload(BaseModel):
    chat_id: int
    media_url: str
    message_type: str
    caption: str | None = None


@router.post("/send-media-link")
async def send_media_link(
    payload: SendMediaLinkPayload,
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    chat = get_chat_by_id(db, payload.chat_id, company_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key or not company.whatsapp_phone_number:
        raise HTTPException(status_code=400, detail="Configuración de YCloud inválida")
    media_url = payload.media_url
    if media_url.startswith('/media/'):
        full_url = f"{settings.public_url}{media_url}"
    elif media_url.startswith(('http://', 'https://')):
        full_url = media_url
    else:
        full_url = f"{settings.public_url}{media_url}"
    ycloud_service = create_ycloud_service(company.ycloud_api_key)
    result = await ycloud_service.send_message(
        to=chat.phone_number,
        message=full_url,
        from_number=company.whatsapp_phone_number,
        message_type=payload.message_type,
        caption=payload.caption
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Error enviando media"))
    message_data = MessageCreate(
        chat_id=payload.chat_id,
        content=payload.caption or "",
        message_type=payload.message_type,
        direction="outgoing",
        user_id=user_id,
        whatsapp_message_id=result.get("message_id"),
        sender_name="Agente",
        attachment_url=payload.media_url
    )
    message = create_message(db, message_data)
    return {
        "success": True,
        "message_id": message.id,
        "whatsapp_message_id": result.get("message_id"),
    }


