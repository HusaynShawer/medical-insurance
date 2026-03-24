from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Appointment, DoctorSlot

VALID_TRANSITIONS = {
    "pending":   ["confirmed", "cancelled"],
    "confirmed": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}

async def update_appointment_status(
    appointment_id: int,
    new_status: str,
    session: AsyncSession,
) -> Appointment:

    result = await session.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise ValueError(f" الحجز رقم {appointment_id} غير موجود")

    allowed = VALID_TRANSITIONS.get(appointment.status, [])
    if new_status not in allowed:
        raise ValueError(
            f" لا يمكن تغيير الحالة من '{appointment.status}' إلى '{new_status}'. "
            f"الحالات المسموحة: {allowed or ['لا يوجد — حالة نهائية']}"
        )

    # لو اتلغى الحجز → نفتح الـ slot تاني
    if new_status == "cancelled":
        slot_result = await session.execute(
            select(DoctorSlot).where(
                DoctorSlot.doctor_id == appointment.doctor_id,
                DoctorSlot.slot_date == appointment.appointment_date,
            )
        )
        slot = slot_result.scalar_one_or_none()
        if slot:
            slot.is_available = True

    appointment.status = new_status
    await session.commit()
    await session.refresh(appointment)

    return appointment


async def get_appointment(
    appointment_id: int,
    session: AsyncSession,
) -> Appointment:

    result = await session.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise ValueError(f" الحجز رقم {appointment_id} غير موجود")

    return appointment


async def get_all_appointments(session: AsyncSession) -> list[Appointment]:
    result = await session.execute(select(Appointment))
    return result.scalars().all()
