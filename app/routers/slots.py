from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date, time
from app.database import get_session
from app.models import Doctor, DoctorSlot

router = APIRouter(prefix="/slots", tags=["Slots"])


# =============================================
# Schemas
# =============================================
class SlotOut(BaseModel):
    id:         int
    slot_date:  date
    slot_time:  time

    class Config:
        from_attributes = True

class DoctorSlotsResponse(BaseModel):
    doctor_id:       int
    doctor_name:     str
    specialization:  str
    available_slots: list[SlotOut]


# =============================================
# GET /slots/{doctor_id}
# =============================================
@router.get("/{doctor_id}", response_model=DoctorSlotsResponse)
async def get_available_slots(
    doctor_id: int,
    session: AsyncSession = Depends(get_session),
):
    # تحقق إن الدكتور موجود
    result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="❌ الدكتور غير موجود")

    # جيب الـ slots المتاحة من النهارده للأمام
    today = date.today()
    result = await session.execute(
        select(DoctorSlot)
        .where(
            DoctorSlot.doctor_id == doctor_id,
            DoctorSlot.slot_date >= today,
            DoctorSlot.is_available == True,
        )
        .order_by(DoctorSlot.slot_date, DoctorSlot.slot_time)
    )
    slots = result.scalars().all()

    if not slots:
        raise HTTPException(
            status_code=404,
            detail=f"❌ لا توجد مواعيد متاحة للدكتور {doctor.name}"
        )

    return {
        "doctor_id":       doctor.id,
        "doctor_name":     doctor.name,
        "specialization":  doctor.specialization,
        "available_slots": slots,
    }