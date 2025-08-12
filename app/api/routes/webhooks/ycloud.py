from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.chats import get_or_create_chat, create_message
from app.services.media_handler import media_handler
from app.schemas.chats.chat import MessageCreate
from app.models.companies.company import Company
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ycloud")
async def ycloud_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook endpoint para recibir eventos de YCloud WhatsApp
    """
    try:
        # Obtener el cuerpo de la petición
        body = await request.body()
        headers = dict(request.headers)
        
        # Log de la petición recibida
        logger.info(f"Webhook YCloud recibido:")
        logger.info(f"Headers: {headers}")
        logger.info(f"Body: {body.decode('utf-8')}")
        
        # Parsear el JSON
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Obtener el tipo de evento
        event_type = payload.get('type', 'unknown')
        logger.info(f"Tipo de evento: {event_type}")
        
        # Procesar diferentes tipos de eventos
        if event_type == 'whatsapp.inbound_message.received':
            await handle_inbound_message(payload, db)
        elif event_type == 'whatsapp.message.updated':
            await handle_message_updated(payload, db)
        elif event_type.startswith('whatsapp.'):
            await handle_whatsapp_event(payload, db)
        else:
            logger.info(f"Evento no manejado: {event_type}")
        
        # Responder con éxito (YCloud espera un 200)
        return {"status": "success", "message": "Webhook procesado"}
        
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_inbound_message(payload: dict, db: Session):
    """Manejar mensajes entrantes de WhatsApp"""
    try:
        logger.info("📨 Procesando mensaje entrante de WhatsApp")
        
        # Extraer información del mensaje - YCloud estructura
        whatsapp_message = payload.get('whatsappInboundMessage', {})
        
        # Información del remitente
        from_number = whatsapp_message.get('from')
        customer_profile = whatsapp_message.get('customerProfile', {})
        customer_name = customer_profile.get('name', 'Desconocido')
        
        # Información del mensaje
        message_text = ""
        attachment_url = None
        message_type = whatsapp_message.get('type')
        
        if message_type == 'text':
            text_data = whatsapp_message.get('text', {})
            message_text = text_data.get('body', '')
        elif message_type == 'image':
            image_data = whatsapp_message.get('image', {})
            attachment_url = image_data.get('link')
            message_text = image_data.get('caption', '[Imagen]')
        elif message_type == 'audio':
            audio_data = whatsapp_message.get('audio', {})
            attachment_url = audio_data.get('link')
            message_text = '[Audio]'
        elif message_type == 'video':
            video_data = whatsapp_message.get('video', {})
            attachment_url = video_data.get('link')
            message_text = video_data.get('caption', '[Video]')
        elif message_type == 'document':
            document_data = whatsapp_message.get('document', {})
            attachment_url = document_data.get('link')
            filename = document_data.get('filename', 'documento')
            message_text = f'[Documento: {filename}]'
        elif message_type == 'sticker':
            sticker_data = whatsapp_message.get('sticker', {})
            attachment_url = sticker_data.get('link')
            message_text = '[Sticker]'
        else:
            message_text = f'[Mensaje de tipo {message_type}]'
        
        # IDs importantes
        message_id = whatsapp_message.get('id')
        wamid = whatsapp_message.get('wamid')
        to_number = whatsapp_message.get('to')
        
        logger.info(f"👤 De: {from_number} ({customer_name})")
        logger.info(f"📱 Para: {to_number}")
        logger.info(f"💬 Mensaje: {message_text}")
        if attachment_url:
            logger.info(f"📎 Archivo adjunto: {attachment_url}")
        logger.info(f"🆔 ID: {message_id}")
        logger.info(f"🔗 WAMID: {wamid}")
        
        # Buscar la empresa que tiene configurado este número de WhatsApp
        company = db.query(Company).filter(
            Company.whatsapp_phone_number == to_number
        ).first()
        
        if not company:
            logger.warning(f"No se encontró empresa para el número {to_number}")
            return
        
        logger.info(f"🏢 Empresa encontrada: {company.nombre}")
        
        # Crear o obtener el chat
        chat = get_or_create_chat(
            db=db,
            company_id=company.id,
            phone_number=from_number,
            customer_name=customer_name
        )
        
        logger.info(f"💬 Chat ID: {chat.id}")
        
        # Si hay archivo adjunto, descargarlo y guardarlo localmente
        local_attachment_url = attachment_url
        if attachment_url:
            logger.info(f"📥 Descargando archivo multimedia...")
            local_path = media_handler.download_and_save_media(
                media_url=attachment_url,
                company_id=company.id,
                chat_id=chat.id,
                message_id=message_id,
                mime_type=whatsapp_message.get(message_type, {}).get('mime_type') if message_type in ['image', 'audio', 'video', 'document', 'sticker'] else None
            )
            if local_path:
                local_attachment_url = local_path
                logger.info(f"✅ Archivo guardado localmente: {local_path}")
            else:
                logger.warning(f"⚠️ No se pudo descargar el archivo, usando URL original")
        
        # Crear el mensaje en la base de datos
        message_data = MessageCreate(
            chat_id=chat.id,
            content=message_text,
            message_type=message_type or "text",
            direction="incoming",
            whatsapp_message_id=message_id,
            wamid=wamid,
            sender_name=customer_name,
            attachment_url=local_attachment_url  # Usar la URL local si se descargó correctamente
        )
        
        message = create_message(db, message_data)
        logger.info(f"✅ Mensaje guardado con ID: {message.id}")
        
        # TODO: Aquí puedes agregar:
        # 1. Respuestas automáticas
        # 2. Asignación automática de agentes
        # 3. Análisis de sentimientos
        
    except Exception as e:
        logger.error(f"Error manejando mensaje entrante: {e}")
        raise


async def handle_message_updated(payload: dict, db: Session):
    """Manejar actualizaciones de estado de mensajes"""
    try:
        logger.info("🔄 Procesando actualización de mensaje")
        
        message_data = payload.get('data', {})
        message_id = message_data.get('id')
        status = message_data.get('status')
        
        logger.info(f"Mensaje {message_id} cambió a estado: {status}")
        
        # Estados posibles: sent, delivered, read, failed
        # Aquí puedes actualizar el estado del mensaje en tu base de datos
        
    except Exception as e:
        logger.error(f"Error manejando actualización de mensaje: {e}")


async def handle_whatsapp_event(payload: dict, db: Session):
    """Manejar otros eventos de WhatsApp"""
    try:
        event_type = payload.get('type')
        logger.info(f"🔔 Procesando evento WhatsApp: {event_type}")
        
        # Manejar otros eventos como:
        # - whatsapp.business_account.updated
        # - whatsapp.phone_number.quality_updated
        # - whatsapp.template.reviewed
        # etc.
        
    except Exception as e:
        logger.error(f"Error manejando evento WhatsApp: {e}")


@router.get("/ycloud/test")
async def test_webhook():
    """Endpoint de prueba para verificar que el webhook está funcionando"""
    return {
        "status": "ok",
        "message": "Webhook de YCloud está funcionando",
        "timestamp": "2025-08-11T00:00:00Z"
    }
