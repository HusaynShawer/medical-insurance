from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from app.models import Doctor, DoctorSlot, DoctorNetwork, Policy, Customer
from app.services.validation_service import run_all_validations
from app.services.booking_service import confirm_booking as _confirm_booking


async def search_doctors(
    national_id: str,
    symptom: str,
    session: AsyncSession,
) -> dict:
    try:
        customer, policy = await run_all_validations(national_id, session)
    except ValueError as e:
        return {"error": str(e)}

    result = await session.execute(
        select(Doctor)
        .join(DoctorNetwork, DoctorNetwork.doctor_id == Doctor.id)
        .where(DoctorNetwork.package_id == policy.package_id)
    )
    all_doctors = result.scalars().all()

    if not all_doctors:
        return {
            "error": f"لا يوجد أطباء في شبكة تأمين العميل",
            "customer_name": customer.name,
            "city": customer.city,
        }

    return {
        "customer_name": customer.name,
        "city": customer.city,
        "package_id": policy.package_id,
        "symptom_received": symptom,
        "doctors": [
            {
                "id": d.id,
                "name": d.name,
                "specialization": d.specialization,
                "city": d.city,
            }
            for d in all_doctors
        ]
    }


async def get_slots(
    doctor_id: int,
    session: AsyncSession,
) -> dict:
    result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = result.scalar_one_or_none()

    if not doctor:
        return {"error": "الدكتور غير موجود"}

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
        return {
            "error": f"لا توجد مواعيد متاحة للدكتور {doctor.name}",
            "doctor_name": doctor.name,
        }

    return {
        "doctor_id": doctor.id,
        "doctor_name": doctor.name,
        "specialization": doctor.specialization,
        "slots": [
            {
                "id": s.id,
                "date": str(s.slot_date),
                "time": str(s.slot_time),
            }
            for s in slots
        ]
    }


async def confirm_booking(
    national_id: str,
    doctor_id: int,
    slot_id: int,
    session: AsyncSession,
) -> dict:
    try:
        result = await _confirm_booking(
            national_id=national_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            session=session,
        )
        return {"success": True, **result}
    except ValueError as e:
        return {"error": str(e)}


TOOL_EXECUTORS = {
    "search_doctors": search_doctors,
    "get_slots": get_slots,
    "confirm_booking": confirm_booking,
}
