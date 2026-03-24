from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_session
from app.models import Appointment, DoctorSlot, Customer, Doctor
from app.services.status_service import (
    update_appointment_status,
    get_appointment,
    get_all_appointments,
)
from app.schemas.appointments import StatusUpdate,AppointmentOut

router = APIRouter(prefix="/appointments", tags=["Appointments"])




# ─────────────────────────────────────────────
# GET /appointments/
# List all with optional status filter
# ─────────────────────────────────────────────
@router.get("/")
async def list_appointments(
    status: Optional[str] = Query(None, description="Filter by status: pending | confirmed | completed | cancelled"),
    session: AsyncSession = Depends(get_session),
):
    query = select(Appointment)
    if status:
        query = query.where(Appointment.status == status)
    result = await session.execute(query.order_by(Appointment.appointment_date.desc()))
    appointments = result.scalars().all()

    enriched = []
    for a in appointments:
        customer = await session.get(Customer, a.customer_id)
        doctor   = await session.get(Doctor, a.doctor_id)

        # Get slot time
        slot_result = await session.execute(
            select(DoctorSlot).where(
                DoctorSlot.doctor_id == a.doctor_id,
                DoctorSlot.slot_date == a.appointment_date,
            )
        )
        slot = slot_result.scalar_one_or_none()

        enriched.append({
            "id":               a.id,
            "customer_id":      a.customer_id,
            "customer_name":    customer.name if customer else None,
            "doctor_id":        a.doctor_id,
            "doctor_name":      doctor.name if doctor else None,
            "appointment_date": a.appointment_date,
            "appointment_time": str(slot.slot_time) if slot else None,
            "status":           a.status,
        })

    return {
        "total":        len(enriched),
        "appointments": enriched,
    }


# ─────────────────────────────────────────────
# GET /appointments/{appointment_id}
# ─────────────────────────────────────────────
@router.get("/{appointment_id}")
async def get_one(
    appointment_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        a = await get_appointment(appointment_id, session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    customer = await session.get(Customer, a.customer_id)
    doctor   = await session.get(Doctor, a.doctor_id)
    slot_result = await session.execute(
        select(DoctorSlot).where(
            DoctorSlot.doctor_id == a.doctor_id,
            DoctorSlot.slot_date == a.appointment_date,
        )
    )
    slot = slot_result.scalar_one_or_none()

    return {
        "id":               a.id,
        "customer_id":      a.customer_id,
        "customer_name":    customer.name if customer else None,
        "doctor_id":        a.doctor_id,
        "doctor_name":      doctor.name if doctor else None,
        "appointment_date": a.appointment_date,
        "appointment_time": str(slot.slot_time) if slot else None,
        "status":           a.status,
    }


# ─────────────────────────────────────────────
# GET /appointments/customer/{national_id}
# All appointments for a specific customer
# ─────────────────────────────────────────────
@router.get("/customer/{national_id}")
async def get_customer_appointments(
    national_id: str,
    session: AsyncSession = Depends(get_session),
):
    customer_result = await session.execute(
        select(Customer).where(Customer.national_id == national_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail=" العميل غير موجود")

    result = await session.execute(
        select(Appointment)
        .where(Appointment.customer_id == customer.id)
        .order_by(Appointment.appointment_date.desc())
    )
    appointments = result.scalars().all()

    enriched = []
    for a in appointments:
        doctor = await session.get(Doctor, a.doctor_id)
        slot_result = await session.execute(
            select(DoctorSlot).where(
                DoctorSlot.doctor_id == a.doctor_id,
                DoctorSlot.slot_date == a.appointment_date,
            )
        )
        slot = slot_result.scalar_one_or_none()
        enriched.append({
            "id":               a.id,
            "doctor_id":        a.doctor_id,
            "doctor_name":      doctor.name if doctor else None,
            "appointment_date": a.appointment_date,
            "appointment_time": str(slot.slot_time) if slot else None,
            "status":           a.status,
        })

    return {
        "customer_id":    customer.id,
        "customer_name":  customer.name,
        "national_id":    customer.national_id,
        "total":          len(enriched),
        "appointments":   enriched,
    }


# ─────────────────────────────────────────────
# PATCH /appointments/{appointment_id}/status
# Change status with valid transition rules
# ─────────────────────────────────────────────
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
            detail=f" الحالة '{body.status}' غير صحيحة. المسموح: {allowed_statuses}",
        )
    try:
        a = await update_appointment_status(appointment_id, body.status, session)
        return {
            "message":          f" تم تغيير الحالة إلى '{a.status}'",
            "appointment_id":   a.id,
            "status":           a.status,
            "appointment_date": a.appointment_date,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────
# DELETE /appointments/{appointment_id}
# Cancel appointment → free the slot → delete record
# This is the endpoint that unblocks re-booking
# ─────────────────────────────────────────────
@router.delete("/{appointment_id}")
async def cancel_and_delete_appointment(
    appointment_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail=f" الحجز رقم {appointment_id} غير موجود")

    if appointment.status == "completed":
        raise HTTPException(
            status_code=400,
            detail=" لا يمكن حذف حجز مكتمل",
        )

    # Free the linked slot so the customer (or anyone) can book again
    slot_result = await session.execute(
        select(DoctorSlot).where(
            DoctorSlot.doctor_id == appointment.doctor_id,
            DoctorSlot.slot_date == appointment.appointment_date,
        )
    )
    slot = slot_result.scalar_one_or_none()
    if slot:
        slot.is_available = True

    customer = await session.get(Customer, appointment.customer_id)
    doctor   = await session.get(Doctor, appointment.doctor_id)

    await session.delete(appointment)
    await session.commit()

    return {
        "message":          f" تم حذف الحجز رقم {appointment_id} وتحرير الميعاد",
        "appointment_id":   appointment_id,
        "customer_name":    customer.name if customer else None,
        "doctor_name":      doctor.name if doctor else None,
        "freed_slot_date":  str(appointment.appointment_date),
        "note":             "يمكن للعميل الحجز مجدداً الآن",
    }