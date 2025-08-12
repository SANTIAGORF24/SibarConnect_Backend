import os
import zipfile
import tempfile
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.chats import get_or_create_chat, create_message
from app.schemas.chats.chat import MessageCreate
from app.models.chats.chat import Message
import logging

logger = logging.getLogger(__name__)


def parse_whatsapp_chat(chat_content: str) -> List[Dict[str, Any]]:
    """
    Parse el contenido del archivo _chat.txt de WhatsApp
    
    Formato esperado:
    [3/26/25, 8:24:43 p.m.] Santiago Ramirez: Hola mundo
    """
    messages = []
    
    # Limpiar caracteres Unicode invisibles
    chat_content = chat_content.replace('\u202f', ' ')  # Narrow No-Break Space
    chat_content = chat_content.replace('\u00a0', ' ')  # Non-Breaking Space
    chat_content = chat_content.replace('\u2009', ' ')  # Thin Space
    
    lines = chat_content.split('\n')
    
    current_message = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detectar nueva línea de mensaje con patrón [fecha, hora] Nombre: mensaje
        message_pattern = r'\[(\d{1,2}/\d{1,2}/\d{2,4}),\s+(\d{1,2}:\d{2}:\d{2}\s+[ap]\.?\s*m\.?)\]\s+([^:]+):\s*(.*)'
        match = re.match(message_pattern, line)
        
        if match:
            # Si hay un mensaje anterior, guardarlo
            if current_message:
                messages.append(current_message)
            
            date_str, time_str, sender_name, content = match.groups()
            
            # Limpiar y normalizar la cadena de tiempo
            time_str = time_str.strip()
            time_str = re.sub(r'\s+', ' ', time_str)  # Normalizar espacios
            time_str = time_str.replace('a.m.', 'AM').replace('p.m.', 'PM')
            time_str = time_str.replace('a. m.', 'AM').replace('p. m.', 'PM')
            time_str = time_str.replace('am', 'AM').replace('pm', 'PM')
            
            # Parsear fecha y hora
            try:
                # Convertir formato de fecha
                date_parts = date_str.split('/')
                if len(date_parts[2]) == 2:  # Año en formato YY
                    year = 2000 + int(date_parts[2])
                else:
                    year = int(date_parts[2])
                
                date_formatted = f"{date_parts[0]}/{date_parts[1]}/{year}"
                datetime_str = f"{date_formatted} {time_str}"
                
                # Intentar múltiples formatos de fecha
                formats_to_try = [
                    "%m/%d/%Y %I:%M:%S %p",
                    "%m/%d/%Y %H:%M:%S",
                    "%d/%m/%Y %I:%M:%S %p",
                    "%d/%m/%Y %H:%M:%S"
                ]
                
                timestamp = None
                for fmt in formats_to_try:
                    try:
                        timestamp = datetime.strptime(datetime_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if not timestamp:
                    logger.warning(f"No se pudo parsear fecha: {datetime_str}")
                    continue
                
                logger.info(f"Mensaje parseado exitosamente: {sender_name} - {timestamp}")
                
                current_message = {
                    'timestamp': timestamp,
                    'sender_name': sender_name.strip(),
                    'content': content.strip(),
                    'message_type': 'text'
                }
                
                # Detectar archivos multimedia
                if '<adjunto:' in content:
                    media_match = re.search(r'<adjunto:\s*([^>]+)>', content)
                    if media_match:
                        media_filename = media_match.group(1).strip()
                        current_message['media_filename'] = media_filename
                        current_message['message_type'] = detect_media_type(media_filename)
                        current_message['content'] = f"[Archivo multimedia: {media_filename}]"
                
            except Exception as e:
                logger.error(f"Error parseando fecha/hora: {datetime_str} - {e}")
                continue
        else:
            # Línea continuación del mensaje anterior
            if current_message:
                current_message['content'] += '\n' + line
    
    # Agregar el último mensaje
    if current_message:
        messages.append(current_message)
    
    return messages


def detect_media_type(filename: str) -> str:
    """Detectar el tipo de archivo multimedia"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        return 'image'
    elif ext in ['mp4', 'avi', 'mov', 'mkv', 'webm']:
        return 'video'
    elif ext in ['mp3', 'wav', 'ogg', 'opus', 'm4a']:
        return 'audio'
    elif ext in ['pdf', 'doc', 'docx', 'txt']:
        return 'document'
    else:
        return 'file'


def extract_phone_number(sender_name: str) -> Optional[str]:
    """
    Intentar extraer número de teléfono del nombre del contacto
    """
    # Buscar patrones de número de teléfono
    phone_patterns = [
        r'\+(\d{10,15})',  # +573154852832
        r'(\d{10,15})',    # 573154852832
        r'\+(\d{1,3})\s*(\d{10})',  # +57 3154852832
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, sender_name)
        if match:
            if len(match.groups()) == 1:
                return '+' + match.group(1)
            else:
                return '+' + ''.join(match.groups())
    
    return None


def save_media_file(media_data: bytes, filename: str, company_id: int) -> str:
    """
    Guardar archivo multimedia en el sistema de archivos
    """
    # Crear directorio para archivos de la empresa
    media_dir = f"media/company_{company_id}/whatsapp_imports"
    os.makedirs(media_dir, exist_ok=True)
    
    # Generar nombre único para evitar conflictos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
    unique_filename = f"{timestamp}_{safe_filename}"
    
    file_path = os.path.join(media_dir, unique_filename)
    
    with open(file_path, 'wb') as f:
        f.write(media_data)
    
    return file_path


async def import_whatsapp_chat(
    zip_file_path: str, 
    company_id: int, 
    db: Session
) -> Dict[str, Any]:
    """
    Importar un chat completo de WhatsApp desde un archivo ZIP
    """
    result = {
        'success': False,
        'messages_imported': 0,
        'media_files_saved': 0,
        'chat_id': None,
        'errors': []
    }
    
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # Buscar el archivo _chat.txt
            chat_file = None
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith('_chat.txt'):
                    chat_file = file_info.filename
                    break
            
            if not chat_file:
                result['errors'].append('No se encontró el archivo _chat.txt en el ZIP')
                return result
            
            # Leer el contenido del chat
            with zip_ref.open(chat_file) as f:
                chat_content = f.read().decode('utf-8', errors='ignore')
            
            # Parsear los mensajes
            messages = parse_whatsapp_chat(chat_content)
            
            if not messages:
                result['errors'].append('No se pudieron parsear mensajes del archivo')
                return result
            
            # Determinar el chat (buscar números de teléfono)
            chat_participants = set()
            for msg in messages:
                phone = extract_phone_number(msg['sender_name'])
                if phone:
                    chat_participants.add(phone)
            
            # Si no se encontraron números, usar el primer contacto como nombre
            if not chat_participants:
                first_sender = messages[0]['sender_name']
                phone_number = '+000000000'  # Placeholder
                customer_name = first_sender
            else:
                # Usar el primer número encontrado
                phone_number = list(chat_participants)[0]
                customer_name = messages[0]['sender_name']
            
            # Crear o obtener el chat
            chat = get_or_create_chat(
                db=db,
                company_id=company_id,
                phone_number=phone_number,
                customer_name=customer_name
            )
            
            result['chat_id'] = chat.id
            
            # Importar mensajes
            for msg in messages:
                try:
                    # Determinar dirección del mensaje
                    sender_phone = extract_phone_number(msg['sender_name'])
                    direction = 'incoming' if sender_phone == phone_number else 'outgoing'
                    
                    # Crear mensaje
                    message_data = MessageCreate(
                        chat_id=chat.id,
                        content=msg['content'],
                        message_type=msg['message_type'],
                        direction=direction,
                        sender_name=msg['sender_name'],
                        timestamp=msg['timestamp']
                    )
                    
                    create_message(db, message_data)
                    result['messages_imported'] += 1
                    
                    # Guardar archivo multimedia si existe
                    if 'media_filename' in msg:
                        try:
                            # Buscar el archivo multimedia en el ZIP (puede estar en subdirectorios)
                            media_found = False
                            for file_info in zip_ref.filelist:
                                if msg['media_filename'] in file_info.filename:
                                    media_data = zip_ref.read(file_info.filename)
                                    media_path = save_media_file(
                                        media_data, 
                                        msg['media_filename'], 
                                        company_id
                                    )
                                    
                                    # Actualizar el mensaje con la ruta del archivo
                                    message = db.query(Message).filter(
                                        Message.chat_id == chat.id,
                                        Message.content == msg['content']
                                    ).order_by(Message.created_at.desc()).first()
                                    
                                    if message:
                                        message.attachment_url = f"/api/chats/media/{company_id}/{os.path.basename(media_path)}"
                                        db.commit()
                                    
                                    result['media_files_saved'] += 1
                                    media_found = True
                                    break
                            
                            if not media_found:
                                logger.warning(f"Archivo multimedia no encontrado en ZIP: {msg['media_filename']}")
                                
                        except Exception as e:
                            logger.warning(f"Error guardando multimedia {msg['media_filename']}: {e}")
                
                except Exception as e:
                    logger.error(f"Error importando mensaje: {e}")
                    result['errors'].append(f"Error en mensaje: {str(e)}")
            
            result['success'] = True
            
    except Exception as e:
        logger.error(f"Error general importando chat: {e}")
        result['errors'].append(f"Error general: {str(e)}")
    
    return result
