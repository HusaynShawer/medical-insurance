from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_session
from app.services.status_service import (
    update_appointment_status,
    get_appointment,
    get_all_appointments,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


class StatusUpdate(BaseModel):
    status: str


@router.get("/")
async def list_appointments(session: AsyncSession = Depends(get_session)):
    appointments = await get_all_appointments(session)
    return [
        {
            "id":               a.id,
            "customer_id":      a.customer_id,
            "doctor_id":        a.doctor_id,
            "appointment_date": a.appointment_date,
            "status":           a.status,
        }
        for a in appointments
    ]


@router.get("/{appointment_id}")
async def get_one(
    appointment_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        a = await get_appointment(appointment_id, session)
        return {
            "id":               a.id,
            "customer_id":      a.customer_id,
            "doctor_id":        a.doctor_id,
            "appointment_date": a.appointment_date,
            "status":           a.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{appointment_id}/status")
async def change_status(
    appointment_id: int,
    body: StatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    allowed_statuses = ["confirmed", "completed", "cancelled"]
    if body.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"❌ الحالة '{body.status}' غير صحيحة. المسموح: {allowed_statuses}"
        )

    try:
        a = await update_appointment_status(appointment_id, body.status, session)
        return {
            "message":          f"✅ تم تغيير الحالة إلى '{a.status}'",
            "appointment_id":   a.id,
            "status":           a.status,
            "appointment_date": a.appointment_date,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))