from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.services.chats import (
    list_appointments_by_chat,
    create_appointment,
    update_appointment,
    delete_appointment,
)
from app.models.chats.chat import Appointment
from app.schemas.chats.chat import CreateAppointmentRequest

router = APIRouter()


@router.get("/appointments")
def list_appointments(
    request: Request,
    chat_id: str | None = None,
    company_id: str | None = None,
    db: Session = Depends(get_db)
):
    chat_id_val = chat_id or request.query_params.get("chat_id")
    company_id_val = company_id or request.query_params.get("company_id")
    try:
        chat_id_int = int(chat_id_val) if chat_id_val is not None else None
        company_id_int = int(company_id_val) if company_id_val is not None else None
    except Exception:
        raise HTTPException(status_code=400, detail="Parámetros inválidos")
    if chat_id_int is None or company_id_int is None:
        raise HTTPException(status_code=400, detail="Faltan parámetros chat_id o company_id")
    appts = list_appointments_by_chat(db, company_id_int, chat_id_int)
    return [
        {
            "id": a.id,
            "company_id": a.company_id,
            "chat_id": a.chat_id,
            "assigned_user_id": a.assigned_user_id,
            "start_at": a.start_at,
        }
        for a in appts
    ]


@router.post("/appointments")
def create_appointment_endpoint(
    data: CreateAppointmentRequest,
    company_id: int,
    db: Session = Depends(get_db)
):
    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.company_id == company_id,
            Appointment.assigned_user_id == data.assigned_user_id,
            Appointment.start_at == data.start_at,
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail={
            "conflict": True,
            "appointment": {
                "id": conflict.id,
                "company_id": conflict.company_id,
                "chat_id": conflict.chat_id,
                "assigned_user_id": conflict.assigned_user_id,
                "start_at": conflict.start_at,
            }
        })
    appt = create_appointment(db, company_id, data.chat_id, data.assigned_user_id, data.start_at)
    return {
        "id": appt.id,
        "company_id": appt.company_id,
        "chat_id": appt.chat_id,
        "assigned_user_id": appt.assigned_user_id,
        "start_at": appt.start_at,
    }


@router.put("/appointments/{appointment_id}")
def update_appointment_endpoint(
    appointment_id: int,
    company_id: int,
    data: dict,
    db: Session = Depends(get_db)
):
    appt = update_appointment(
        db,
        company_id,
        appointment_id,
        assigned_user_id=data.get("assigned_user_id"),
        start_at=data.get("start_at"),
    )
    if appt is None:
        raise HTTPException(status_code=400, detail="No se pudo actualizar (conflicto o no existe)")
    return {
        "id": appt.id,
        "company_id": appt.company_id,
        "chat_id": appt.chat_id,
        "assigned_user_id": appt.assigned_user_id,
        "start_at": appt.start_at,
    }


@router.delete("/appointments/{appointment_id}")
def delete_appointment_endpoint(
    appointment_id: int,
    company_id: int,
    db: Session = Depends(get_db)
):
    ok = delete_appointment(db, company_id, appointment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return {"success": True}


