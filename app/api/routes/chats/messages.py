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
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 Iniciando envío de archivo: {file.filename}")
    logger.info(f"📊 Parámetros: company_id={company_id}, user_id={user_id}, chat_id={chat_id}")
    
    chat = get_chat_by_id(db, chat_id, company_id)
    if not chat:
        logger.error(f"❌ Chat no encontrado: chat_id={chat_id}, company_id={company_id}")
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    company = get_company(db, company_id)
    if not company or not company.ycloud_api_key:
        logger.error(f"❌ Empresa sin API key: company_id={company_id}")
        raise HTTPException(status_code=400, detail="La empresa no tiene configurada la API de YCloud")
    if not company.whatsapp_phone_number:
        logger.error(f"❌ Empresa sin número WhatsApp: company_id={company_id}")
        raise HTTPException(status_code=400, detail="La empresa no tiene configurado un número de WhatsApp")
    try:
        file_extension = Path(file.filename).suffix.lower() if file.filename else ""
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"📁 Archivo: {file.filename}")
        logger.info(f"🔧 Extensión: {file_extension}")
        logger.info(f"📏 Tamaño: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        
        if file_extension in ['.mp4', '.mov', '.avi']:
            logger.info("🎥 Archivo de video detectado")
            if file_size > 16 * 1024 * 1024:
                error_msg = f"El video es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 16MB"
                logger.error(f"❌ {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.webp']:
            logger.info("🖼️ Archivo de imagen detectado")
            if file_size > 5 * 1024 * 1024:
                error_msg = f"La imagen es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 5MB"
                logger.error(f"❌ {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
        elif file_extension in ['.mp3', '.ogg', '.m4a', '.aac', '.amr']:
            logger.info("🎵 Archivo de audio detectado")
            if file_size > 16 * 1024 * 1024:
                error_msg = f"El audio es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 16MB"
                logger.error(f"❌ {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
        elif file_extension == '.wav':
            logger.info("🎵 Archivo con extensión .wav detectado - verificando formato real...")
            
            # Detectar el formato real del archivo
            if content.startswith(b'RIFF') and b'WAVE' in content[8:12]:
                logger.info("✅ Archivo WAV válido detectado, procediendo con conversión...")
                # Continuar con la conversión WAV → MP3
                try:
                    from pydub import AudioSegment
                    import tempfile
                    import os
                    
                    # Crear archivo temporal para el WAV
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                        temp_wav.write(content)
                        temp_wav_path = temp_wav.name
                    
                    logger.info(f"💾 Archivo temporal WAV creado: {temp_wav_path}")
                    
                    # Convertir WAV a MP3
                    logger.info("🔄 Iniciando conversión WAV → MP3...")
                    audio = AudioSegment.from_wav(temp_wav_path)
                    temp_mp3_path = temp_wav_path.replace('.wav', '.mp3')
                    audio.export(temp_mp3_path, format='mp3')
                    logger.info(f"💾 Archivo temporal MP3 creado: {temp_mp3_path}")
                    
                    # Leer el MP3 convertido
                    with open(temp_mp3_path, 'rb') as mp3_file:
                        content = mp3_file.read()
                    
                    # Limpiar archivos temporales
                    os.unlink(temp_wav_path)
                    os.unlink(temp_mp3_path)
                    
                    # Actualizar extensión y tamaño
                    file_extension = '.mp3'
                    file_size = len(content)
                    logger.info(f"✅ WAV convertido a MP3 exitosamente")
                    logger.info(f"📏 Nuevo tamaño: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
                    
                except Exception as conv_error:
                    logger.error(f"❌ Error convirtiendo WAV a MP3: {str(conv_error)}")
                    error_msg = "Error convirtiendo archivo WAV a MP3. Por favor, use un archivo MP3 directamente."
                    raise HTTPException(status_code=400, detail=error_msg)
                    
            elif content.startswith(b'\x1a\x45\xdf\xa3'):
                logger.info("🎬 Archivo WebM/Matroska detectado - convirtiendo a MP3...")
                # Convertir WebM/Matroska a MP3
                try:
                    from pydub import AudioSegment
                    import tempfile
                    import os
                    
                    # Crear archivo temporal para el WebM
                    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                        temp_webm.write(content)
                        temp_webm_path = temp_webm.name
                    
                    logger.info(f"💾 Archivo temporal WebM creado: {temp_webm_path}")
                    
                    # Convertir WebM a MP3
                    logger.info("🔄 Iniciando conversión WebM → MP3...")
                    audio = AudioSegment.from_file(temp_webm_path, format="webm")
                    temp_mp3_path = temp_webm_path.replace('.webm', '.mp3')
                    audio.export(temp_mp3_path, format='mp3')
                    logger.info(f"💾 Archivo temporal MP3 creado: {temp_mp3_path}")
                    
                    # Leer el MP3 convertido
                    with open(temp_mp3_path, 'rb') as mp3_file:
                        content = mp3_file.read()
                    
                    # Limpiar archivos temporales
                    os.unlink(temp_webm_path)
                    os.unlink(temp_mp3_path)
                    
                    # Actualizar extensión y tamaño
                    file_extension = '.mp3'
                    file_size = len(content)
                    logger.info(f"✅ WebM convertido a MP3 exitosamente")
                    logger.info(f"📏 Nuevo tamaño: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
                    
                except Exception as conv_error:
                    logger.error(f"❌ Error convirtiendo WebM a MP3: {str(conv_error)}")
                    error_msg = "Error convirtiendo archivo WebM a MP3. Por favor, use un archivo MP3 directamente."
                    raise HTTPException(status_code=400, detail=error_msg)
                    
            else:
                logger.error("❌ Formato de archivo no reconocido")
                logger.error(f"🔍 Primeros bytes: {content[:20].hex()}")
                error_msg = "El archivo tiene extensión .wav pero no es un formato de audio reconocido. Por favor, use un archivo MP3, WAV válido, o WebM."
                raise HTTPException(status_code=400, detail=error_msg)
        else:
            logger.info("📄 Archivo de documento detectado")
            if file_size > 100 * 1024 * 1024:
                error_msg = f"El documento es demasiado grande ({file_size / 1024 / 1024:.1f}MB). Máximo permitido: 100MB"
                logger.error(f"❌ {error_msg}")
                raise HTTPException(status_code=400, detail=error_msg)
        
        from uuid import uuid4
        
        # Guardar en la estructura de chat específica (como WhatsApp)
        company_dir = Path(f"media/company_{company_id}/whatsapp/chat_{chat_id}")
        company_dir.mkdir(parents=True, exist_ok=True)
        
        # Usar la extensión actualizada (puede haber cambiado por conversión)
        unique_filename = f"msg_{uuid4()}_{uuid4().hex[:8]}{file_extension}"
        file_path = company_dir / unique_filename
        
        logger.info(f"💾 Guardando archivo en: {company_dir}")
        logger.info(f"💾 Nombre del archivo: {unique_filename}")
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Determinar tipo de mensaje (después de posibles conversiones)
        if file_extension in ['.jpg', '.jpeg', '.png', '.webp']:
            message_type = 'image'
        elif file_extension in ['.mp4', '.mov', '.avi']:
            message_type = 'video'
        elif file_extension in ['.mp3', '.ogg', '.m4a', '.aac', '.amr']:
            message_type = 'audio'
        else:
            message_type = 'document'
        
        logger.info(f"🎯 Tipo de mensaje determinado: {message_type}")
        file_url = f"/media/company_{company_id}/whatsapp/chat_{chat_id}/{unique_filename}"
        
        try:
            from app.core.config import settings
            ycloud_service = create_ycloud_service(company.ycloud_api_key)
            full_file_url = f"{settings.public_url}{file_url}"
            
            logger.info(f"📤 Enviando archivo a WhatsApp...")
            logger.info(f"📱 Número destino: {chat.phone_number}")
            logger.info(f"📱 Número origen: {company.whatsapp_phone_number}")
            logger.info(f"🔗 URL del archivo: {full_file_url}")
            
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


