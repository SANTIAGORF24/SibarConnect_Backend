from fastapi import APIRouter
from .start import router as start_router
from .messages import router as messages_router
from .tags_notes import router as tags_notes_router
from .appointments import router as appointments_router
from .management import router as management_router
from .imports import router as imports_router
from .media import router as media_router
from .ai import router as ai_router
from .realtime import router as realtime_router

router = APIRouter()

# Orden lógico de inclusión para mantener rutas existentes
router.include_router(tags_notes_router)
router.include_router(appointments_router)
router.include_router(imports_router)
router.include_router(media_router)
router.include_router(messages_router)
router.include_router(start_router)
router.include_router(ai_router)
router.include_router(management_router)
router.include_router(realtime_router)

__all__ = ["router"]
