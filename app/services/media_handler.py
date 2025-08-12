import os
import requests
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class MediaHandler:
    """Servicio para descargar y almacenar archivos multimedia localmente"""
    
    def __init__(self, base_media_path: str = None):
        if base_media_path is None:
            # Carpeta media en la raíz del proyecto (un nivel arriba del directorio backend)
            project_root = Path(__file__).parent.parent.parent.parent
            base_media_path = project_root / "media"
        self.base_media_path = Path(base_media_path)
        # Crear directorio base si no existe
        self.base_media_path.mkdir(exist_ok=True)
    
    def download_and_save_media(
        self, 
        media_url: str, 
        company_id: int, 
        chat_id: int, 
        message_id: str,
        mime_type: str = None
    ) -> Optional[str]:
        """
        Descarga un archivo multimedia y lo guarda localmente
        
        Args:
            media_url: URL del archivo multimedia
            company_id: ID de la empresa
            chat_id: ID del chat
            message_id: ID del mensaje
            mime_type: Tipo MIME del archivo
            
        Returns:
            Ruta relativa del archivo guardado o None si falla
        """
        try:
            # Crear estructura de directorios
            company_dir = self.base_media_path / f"company_{company_id}"
            whatsapp_dir = company_dir / "whatsapp" / f"chat_{chat_id}"
            whatsapp_dir.mkdir(parents=True, exist_ok=True)
            
            # Descargar el archivo
            logger.info(f"📥 Descargando media desde: {media_url}")
            response = requests.get(media_url, timeout=30)
            response.raise_for_status()
            
            # Determinar extensión basada en mime_type o URL
            extension = self._get_file_extension(mime_type, media_url)
            
            # Generar nombre de archivo único
            filename = f"msg_{message_id}_{self._generate_hash(media_url)[:8]}{extension}"
            file_path = whatsapp_dir / filename
            
            # Guardar archivo
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Retornar ruta relativa desde el directorio media
            relative_path = f"/media/company_{company_id}/whatsapp/chat_{chat_id}/{filename}"
            logger.info(f"✅ Media guardada en: {relative_path}")
            
            return relative_path
            
        except Exception as e:
            logger.error(f"❌ Error descargando media: {e}")
            return None
    
    def _get_file_extension(self, mime_type: str = None, url: str = None) -> str:
        """Determina la extensión del archivo basada en el tipo MIME o URL"""
        
        # Mapeo de tipos MIME a extensiones
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'audio/ogg': '.ogg',
            'audio/mpeg': '.mp3',
            'audio/mp4': '.m4a',
            'audio/wav': '.wav',
            'video/mp4': '.mp4',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/zip': '.zip',
            'text/plain': '.txt'
        }
        
        # Intentar usar mime_type primero
        if mime_type:
            # Limpiar el mime_type (remover codecs y parámetros adicionales)
            clean_mime = mime_type.split(';')[0].strip()
            if clean_mime in mime_to_ext:
                return mime_to_ext[clean_mime]
        
        # Si no hay mime_type o no se reconoce, intentar extraer de la URL
        if url:
            parsed_url = urlparse(url)
            path = parsed_url.path
            if '.' in path:
                return '.' + path.split('.')[-1]
        
        # Extensión por defecto
        return '.bin'
    
    def _generate_hash(self, content: str) -> str:
        """Genera un hash único para el contenido"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_local_media_url(self, relative_path: str, base_url: str = "http://localhost:8000") -> str:
        """Convierte una ruta relativa en una URL completa para servir el archivo"""
        return f"{base_url}{relative_path}"
    
    def file_exists(self, relative_path: str) -> bool:
        """Verifica si un archivo existe localmente"""
        if not relative_path:
            return False
        
        # Convertir ruta relativa a absoluta
        # Remover /media/ del inicio si existe
        clean_path = relative_path.lstrip('/')
        if clean_path.startswith('media/'):
            clean_path = clean_path[6:]  # Remover 'media/'
        
        full_path = self.base_media_path / clean_path
        return full_path.exists()

# Instancia global del manejador de medios
media_handler = MediaHandler()
