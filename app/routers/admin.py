from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date, time
from app.database import get_session
from app.models import Doctor, DoctorSlot
from app.schemas.admin import SlotCreate, SlotOut
router = APIRouter(prefix="/admin", tags=["Admin"])

# =============================================
# POST /admin/doctors/{doctor_id}/slots
# =============================================


@router.post("/doctors/{doctor_id}/slots", status_code=201)
async def add_slot(
    doctor_id: int,
    body: SlotCreate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="الدكتور غير موجود")

    existing = await session.execute(
        select(DoctorSlot).where(
            DoctorSlot.doctor_id == doctor_id,
            DoctorSlot.slot_date == body.slot_date,
            DoctorSlot.slot_time == body.slot_time,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="هذا الميعاد موجود بالفعل"
        )

    slot = DoctorSlot(
        doctor_id=doctor_id,
        slot_date=body.slot_date,
        slot_time=body.slot_time,
        is_available=True,
    )
    session.add(slot)
    await session.commit()
    await session.refresh(slot)

    return {
        "message":   f"تم إضافة الميعاد للدكتور {doctor.name}",
        "slot_id":   slot.id,
        "slot_date": slot.slot_date,
        "slot_time": str(slot.slot_time),
    }


# =============================================
# GET /admin/doctors/{doctor_id}/slots
# =============================================
@router.get("/doctors/{doctor_id}/slots")
async def get_all_doctor_slots(
    doctor_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="الدكتور غير موجود")

    result = await session.execute(
        select(DoctorSlot)
        .where(DoctorSlot.doctor_id == doctor_id)
        .order_by(DoctorSlot.slot_date, DoctorSlot.slot_time)
    )
    slots = result.scalars().all()

    return {
        "doctor_id":   doctor.id,
        "doctor_name": doctor.name,
        "slots": [
            {
                "id":           s.id,
                "slot_date":    s.slot_date,
                "slot_time":    str(s.slot_time),
                "is_available": s.is_available,
                "status":       "متاح" if s.is_available else "محجوز",
            }
            for s in slots
        ],
        "total":    len(slots),
        "available": sum(1 for s in slots if s.is_available),
        "booked":    sum(1 for s in slots if not s.is_available),
    }


# =============================================
# DELETE /admin/slots/{slot_id}
# =============================================
@router.delete("/slots/{slot_id}")
async def delete_slot(
    slot_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DoctorSlot).where(DoctorSlot.id == slot_id)
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="الميعاد غير موجود")

    if not slot.is_available:
        raise HTTPException(
            status_code=400,
            detail=" لا يمكن حذف ميعاد محجوز — قم بإلغاء الحجز أولاً"
        )

    await session.delete(slot)
    await session.commit()

    return {"message": f" تم حذف الميعاد رقم {slot_id}"}


# =============================================
# GET /admin/doctors/
# =============================================
@router.get("/doctors/")
async def get_all_doctors_summary(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Doctor))
    doctors = result.scalars().all()

    summary = []
    for d in doctors:
        slots_result = await session.execute(
            select(DoctorSlot).where(DoctorSlot.doctor_id == d.id)
        )
        slots = slots_result.scalars().all()
        summary.append({
            "id":             d.id,
            "name":           d.name,
            "specialization": d.specialization,
            "city":           d.city,
            "total_slots":    len(slots),
            "available":      sum(1 for s in slots if s.is_available),
            "booked":         sum(1 for s in slots if not s.is_available),
        })

    return summary
