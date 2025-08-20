from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.chats import (
    create_message,
    get_or_create_chat,
)
from app.services.ycloud import create_ycloud_service
from app.services.companies import get_company
from app.schemas.chats.chat import (
    MessageCreate,
    StartChatRequest,
    StartChatTemplateRequest,
)

router = APIRouter()


@router.post("/start")
async def start_chat_and_send(
    payload: StartChatRequest,
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    phone = payload.phone_number.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone_number requerido")
    phone = phone.replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        normalized = phone
    else:
        normalized = "+" + phone
    chat = get_or_create_chat(db, normalized, company_id, payload.customer_name)
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key or not company.whatsapp_phone_number:
        raise HTTPException(status_code=400, detail="Configuración de YCloud inválida")
    try:
        ycloud_service = create_ycloud_service(company.ycloud_api_key)
        result = await ycloud_service.send_message(
            to=chat.phone_number,
            message=payload.content,
            from_number=company.whatsapp_phone_number,
            message_type=payload.message_type or "text",
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Error enviando mensaje"))
        message_data = MessageCreate(
            chat_id=chat.id,
            content=payload.content,
            message_type=payload.message_type or "text",
            direction="outgoing",
            user_id=user_id,
            whatsapp_message_id=result.get("message_id"),
            sender_name="Agente",
        )
        message = create_message(db, message_data)
        return {
            "success": True,
            "chat_id": chat.id,
            "message_id": message.id,
            "whatsapp_message_id": result.get("message_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/start-template")
async def start_chat_with_template(
    payload: StartChatTemplateRequest,
    company_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    phone = payload.phone_number.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+" + phone
    chat = get_or_create_chat(db, phone, company_id, payload.customer_name)
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key or not company.whatsapp_phone_number:
        raise HTTPException(status_code=400, detail="Configuración de YCloud inválida")
    ycloud_service = create_ycloud_service(company.ycloud_api_key)
    result = await ycloud_service.send_template(
        to=chat.phone_number,
        from_number=company.whatsapp_phone_number,
        template_name=payload.template_name,
        language_code=payload.language_code,
        body_params=payload.body_params or []
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("response") or result.get("error", "Error enviando plantilla"))
    message_data = MessageCreate(
        chat_id=chat.id,
        content=f"[TEMPLATE] {payload.template_name}",
        message_type="template",
        direction="outgoing",
        user_id=user_id,
        whatsapp_message_id=result.get("message_id"),
        sender_name="Agente",
    )
    message = create_message(db, message_data)
    return {"success": True, "chat_id": chat.id, "message_id": message.id, "whatsapp_message_id": result.get("message_id")}


