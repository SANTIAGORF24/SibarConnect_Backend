import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.services.chats import (
    get_messages_by_chat,
    save_chat_summary,
    get_chat_summary,
)
from app.core.config import settings
from google import genai as genai_client
from google.genai import types as genai_types
from app.schemas.chats.chat import (
    CreateSummaryRequest,
    ChatInsightsRequest,
    ChatInsightsOut,
    AssistDraftRequest,
    AssistDraftOut,
)

router = APIRouter(prefix="/ai")


@router.post("/summaries/generate")
async def generate_summary_endpoint(
    data: CreateSummaryRequest,
    company_id: int,
    db: Session = Depends(get_db)
):
    messages = get_messages_by_chat(db, data.chat_id, limit=100)
    text_messages = [m.content for m in reversed(messages) if m.message_type == 'text']
    if not text_messages:
        raise HTTPException(status_code=400, detail="No hay mensajes de texto para resumir")
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY no configurada")
    system_prompt = (
        "Rol: Analista de Conversaciones.\n"
        "Responsabilidades: resumir claro y conciso; identificar temas principales; determinar interés (Interesado/No interesado/Indeciso); señalar información para seguimiento (dudas, objeciones, solicitudes); mantener formato consistente.\n"
        "Formato: \n"
        "Tema principal: …\n"
        "Interés del cliente: Interesado / No interesado / Indeciso\n"
        "Puntos clave tratados: …\n"
        "Observaciones relevantes: …\n"
    )
    user_prompt = (
        "A continuación tienes los últimos mensajes de texto (máximo 100) de una conversación.\n"
        "Solo considera mensajes de texto (ignora imágenes, stickers, documentos, audios).\n"
        "Genera el resumen siguiendo estrictamente el formato indicado.\n\n"
        + "\n".join(text_messages)
    )
    try:
        client = genai_client.Client(api_key=settings.gemini_api_key)
        contents = [genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_prompt)])]
        generate_content_config = genai_types.GenerateContentConfig(
            temperature=0,
            system_instruction=[genai_types.Part.from_text(text=system_prompt)],
        )
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=generate_content_config,
        )
        content = getattr(resp, "text", "") or ""
        if not content:
            raise Exception("Respuesta vacía de Gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error Gemini: {str(e)}")
    text_low = content.lower()
    if "interesado" in text_low and "no interesado" not in text_low and "indeciso" not in text_low:
        interest = "Interesado"
    elif "no interesado" in text_low:
        interest = "No interesado"
    elif "indeciso" in text_low:
        interest = "Indeciso"
    else:
        interest = "Indeciso"
    row = save_chat_summary(db, company_id, data.chat_id, content, interest, provider="gemini", model="gemini-2.5-flash")
    return {
        "id": row.id,
        "summary": row.summary,
        "interest": row.interest,
        "created_at": row.created_at,
    }


@router.get("/summaries/{chat_id}")
def get_summary_endpoint(
    chat_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    row = get_chat_summary(db, company_id, chat_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")
    return {
        "id": row.id,
        "summary": row.summary,
        "interest": row.interest,
        "provider": getattr(row, "provider", "gemini"),
        "model": getattr(row, "model", "gemini-2.5-flash"),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.post("/insights", response_model=ChatInsightsOut)
def chat_insights(payload: ChatInsightsRequest, company_id: int, db: Session = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔍 Iniciando análisis de insights para chat_id: {payload.chat_id}, company_id: {company_id}")
        logger.info(f"📊 Payload recibido: {payload}")
        
        if payload.messages is not None and len(payload.messages) > 0:
            logger.info(f"📨 Usando mensajes del payload: {len(payload.messages)} mensajes")
            text_msgs = [m for m in payload.messages if getattr(m, 'message_type', 'text') == 'text' and getattr(m, 'content', None)]
        else:
            logger.info(f"📥 Obteniendo mensajes de la base de datos para chat_id: {payload.chat_id}")
            msgs = get_messages_by_chat(db, payload.chat_id, limit=payload.limit)
            logger.info(f"📊 Mensajes obtenidos de BD: {len(msgs)} mensajes")
            text_msgs = [m for m in reversed(msgs) if getattr(m, 'message_type', 'text') == 'text' and getattr(m, 'content', None)]
        
        logger.info(f"💬 Mensajes de texto filtrados: {len(text_msgs)} mensajes")
        
        if not text_msgs:
            logger.info("⚠️ No hay mensajes de texto para analizar, retornando respuesta vacía")
            return ChatInsightsOut()
            
        if not settings.gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY no configurada. Por favor, configura la variable de entorno GEMINI_API_KEY en el archivo .env")
            
        system_prompt = (
            "Rol: Analista de Conversaciones y Asistente Comercial.\n"
            "Tarea: Analiza los mensajes (en español) y devuelve SOLO JSON válido con: "
            "message_sentiments (lista de {id?, content?, sentiment in [positive,neutral,negative], score -1..1}), "
            "chat_sentiment ({label,score,trend}), intents (lista), entities (lista de {type,value}), "
            "suggested_actions (lista de {action,reason}), suggested_reply (string), candidate_replies (lista de 3 a 5 strings cortos en español, listos para enviar), "
            "tone_warnings (lista), interest_probability (0..1), churn_risk (0..1).\n"
            "NO uses markdown, NO fences, responde SOLO JSON."
        )
        
        user_payload_lines = []
        for m in text_msgs[-100:]:
            content = getattr(m, 'content', None)
            direction = getattr(m, 'direction', None)
            role = 'user' if direction and direction.lower() == 'incoming' else 'agent'
            if content:
                user_payload_lines.append(f"[{role}] {content}")
                
        user_prompt = (
            "Mensajes recientes (máx. 100). Analiza sentimiento por mensaje y global; detecta intenciones (agendar, compra, soporte, etc.) y entidades (monto, fecha); sugiere siguientes mejores acciones; sugiere respuesta y advertencias de tono. Devuelve JSON.\n\n"
            + "\n".join(user_payload_lines)
        )
        
        logger.info(f"🤖 Enviando prompt a Gemini con {len(user_payload_lines)} mensajes")
        logger.info(f"📝 Longitud del prompt: {len(user_prompt)} caracteres")
        logger.info(f"📝 Primeros 200 caracteres del prompt: '{user_prompt[:200]}...'")
        
        client = genai_client.Client(api_key=settings.gemini_api_key)
        contents = [genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_prompt)])]
        config = genai_types.GenerateContentConfig(temperature=0, system_instruction=[genai_types.Part.from_text(text=system_prompt)])
        resp = client.models.generate_content(model="gemini-1.5-flash", contents=contents, config=config)
        
        logger.info(f"🔍 Respuesta completa de Gemini: {resp}")
        logger.info(f"🔍 Tipo de respuesta: {type(resp)}")
        logger.info(f"🔍 Atributos de respuesta: {dir(resp)}")
        
        raw_text = getattr(resp, "text", "") or ""
        text = raw_text.strip()
        
        logger.info(f"📝 Respuesta de Gemini recibida: {len(text)} caracteres")
        logger.info(f"📝 Contenido de respuesta: '{text}'")
        
        if not text:
            logger.error("❌ Gemini devolvió respuesta vacía")
            logger.error("🔍 Intentando obtener más información del error...")
            
            # Intentar obtener información del error de la respuesta
            if hasattr(resp, 'candidates') and resp.candidates:
                candidate = resp.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    logger.error(f"🔍 Finish reason: {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings'):
                    logger.error(f"🔍 Safety ratings: {candidate.safety_ratings}")
            
            # Intentar con un modelo alternativo
            try:
                logger.info("🔄 Intentando con modelo alternativo gemini-2.5-flash...")
                resp_alt = client.models.generate_content(model="gemini-2.5-flash", contents=contents, config=config)
                raw_text_alt = getattr(resp_alt, "text", "") or ""
                text_alt = raw_text_alt.strip()
                
                if text_alt:
                    logger.info("✅ Modelo alternativo funcionó")
                    text = text_alt
                else:
                    raise HTTPException(status_code=500, detail="Gemini devolvió respuesta vacía con ambos modelos. Verifica la API key y la configuración.")
            except Exception as alt_error:
                logger.error(f"❌ Error con modelo alternativo: {alt_error}")
                raise HTTPException(status_code=500, detail="Gemini devolvió respuesta vacía. Verifica la API key y el modelo.")
        
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        import re
        candidate = text
        if not (candidate.startswith('{') and candidate.endswith('}')):
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                candidate = match.group(0)
                
        logger.info(f"🔍 JSON candidato para parsear: '{candidate}'")
        
        data = json.loads(candidate)
        if not isinstance(data, dict):
            raise ValueError("Respuesta JSON inválida (no dict)")
            
        data.setdefault('message_sentiments', [])
        data.setdefault('chat_sentiment', None)
        data.setdefault('intents', [])
        data.setdefault('entities', [])
        data.setdefault('suggested_actions', [])
        data.setdefault('suggested_reply', None)
        data.setdefault('tone_warnings', [])
        data.setdefault('candidate_replies', [])
        
        logger.info("✅ Insights generados exitosamente")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error decodificando respuesta de Gemini: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error decodificando respuesta de Gemini: {str(e)}")
    except ValueError as e:
        logger.error(f"❌ Error en formato de respuesta: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en formato de respuesta: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error inesperado generando insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado generando insights: {str(e)}")


@router.get("/insights", response_model=ChatInsightsOut)
def chat_insights_get(chat_id: int, company_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return chat_insights(ChatInsightsRequest(chat_id=chat_id, limit=limit), company_id, db)


@router.post("/assist-draft", response_model=AssistDraftOut)
def assist_draft(payload: AssistDraftRequest):
    if not settings.gemini_api_key:
        draft = (payload.draft or "").strip()
        improved = draft
        if improved and not improved.endswith(('.', '!', '?')):
            improved += '.'
        return AssistDraftOut(improved=improved, tone_warnings=[])
    system_prompt = (
        "Rol: Editor de Mensajes para Atención al Cliente.\n"
        "Mejora claridad, ortografía, cortesía y profesionalidad; mantén el significado; sugiere cambios concisos. Devuelve SOLO JSON: {improved: string, tone_warnings: string[]}."
    )
    user_prompt = f"Mensaje borrador a mejorar:\n\n{payload.draft}\n\nResponde SOLO JSON."
    try:
        client = genai_client.Client(api_key=settings.gemini_api_key)
        contents = [genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_prompt)])]
        config = genai_types.GenerateContentConfig(temperature=0, system_instruction=[genai_types.Part.from_text(text=system_prompt)])
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=contents, config=config)
        text = getattr(resp, "text", "") or ""
        import json
        data = json.loads(text)
        if not isinstance(data, dict) or 'improved' not in data:
            raise ValueError("Respuesta JSON inválida")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error asistiendo borrador: {str(e)}")

