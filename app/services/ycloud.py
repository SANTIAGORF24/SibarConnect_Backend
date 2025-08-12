import httpx
import json
from typing import Dict, Any
from app.schemas.companies.company import YCloudTestResult
from app.core.config import settings


class YCloudService:
    """Servicio para integración con YCloud WhatsApp API"""
    
    BASE_URL = "https://api.ycloud.com/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
    
    async def test_connection(self) -> YCloudTestResult:
        """Prueba la conexión con YCloud API"""
        try:
            async with httpx.AsyncClient() as client:
                # Obtener los números de teléfono asociados a la cuenta
                response = await client.get(
                    f"{self.BASE_URL}/whatsapp/phoneNumbers",
                    headers=self.headers,
                    timeout=10.0
                )
                
                print(f"YCloud Response Status: {response.status_code}")
                print(f"YCloud Response: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"YCloud Data: {data}")
                    
                    phone_numbers = data.get("phoneNumbers", [])
                    
                    if phone_numbers:
                        # Obtener el primer número de teléfono disponible
                        phone_data = phone_numbers[0]
                        phone_number = phone_data.get("phoneNumber")
                        status = phone_data.get("status", "unknown")
                        display_name = phone_data.get("displayPhoneNumber", phone_number)
                        verified = phone_data.get("verifiedName", "No verificado")
                        
                        return YCloudTestResult(
                            success=True,
                            message=f"Conexión exitosa! Número: {display_name} - Estado: {status} - Verificado: {verified}",
                            phone_number=phone_number,
                            webhook_status=status
                        )
                    else:
                        return YCloudTestResult(
                            success=True,
                            message="API Key válida, pero no tienes números de WhatsApp Business configurados en tu cuenta YCloud",
                            phone_number=None,
                            webhook_status="no_numbers"
                        )
                        
                elif response.status_code == 401:
                    return YCloudTestResult(
                        success=False,
                        message="API Key inválida o expirada"
                    )
                elif response.status_code == 403:
                    return YCloudTestResult(
                        success=False,
                        message="Acceso denegado. Verifica los permisos de tu API Key"
                    )
                else:
                    return YCloudTestResult(
                        success=False,
                        message=f"Error de conexión: {response.status_code}"
                    )
                    
        except httpx.TimeoutException:
            return YCloudTestResult(
                success=False,
                message="Timeout al conectar con YCloud. Verifica tu conexión a internet"
            )
        except httpx.RequestError as e:
            return YCloudTestResult(
                success=False,
                message=f"Error de red: {str(e)}"
            )
        except Exception as e:
            return YCloudTestResult(
                success=False,
                message=f"Error inesperado: {str(e)}"
            )
    
    async def get_phone_numbers(self) -> Dict[str, Any]:
        """Obtiene los números de teléfono disponibles"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/whatsapp/phoneNumbers",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    
    async def send_message(self, to: str, message: str, from_number: str, message_type: str = "text") -> Dict[str, Any]:
        """Envía un mensaje de WhatsApp"""
        try:
            # Formatear número de teléfono (asegurar que tenga formato internacional)
            if not to.startswith('+'):
                to = f"+{to}"
            
            if not from_number.startswith('+'):
                from_number = f"+{from_number}"
            
            payload = {
                "to": to,
                "from": from_number,
                "type": message_type,
            }
            
            if message_type == "text":
                payload["text"] = {
                    "body": message
                }
            elif message_type == "sticker":
                # Para stickers, convertir ruta local a URL pública accesible
                sticker_url = message
                if message.startswith('/media/'):
                    # Convertir ruta local a URL pública (ngrok)
                    sticker_url = f"{settings.public_url}{message}"
                elif not message.startswith(('http://', 'https://')):
                    # Si no es una URL completa, asumir que es ruta local
                    sticker_url = f"{settings.public_url}{message}"
                
                print(f"🔗 Sticker URL construida: {sticker_url}")
                
                payload["sticker"] = {
                    "link": sticker_url
                }
            else:
                # Para otros tipos de mensajes en el futuro
                payload["text"] = {
                    "body": message
                }
            
            print(f"Enviando mensaje desde {from_number} a {to}: {message}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/whatsapp/messages",
                    headers=self.headers,
                    json=payload,
                    timeout=10.0
                )
                
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "message_id": result.get("id"),
                        "status": result.get("status", "sent"),
                        "response": result
                    }
                else:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                    return {
                        "success": False,
                        "error": f"Error {response.status_code}: {error_data.get('error', 'Error desconocido')}",
                        "response": error_data
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Timeout al enviar mensaje"
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Error de red: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error inesperado: {str(e)}"
            }


def create_ycloud_service(api_key: str) -> YCloudService:
    """Factory para crear una instancia del servicio YCloud"""
    return YCloudService(api_key)
