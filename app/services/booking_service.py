from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.models import Appointment, Doctor, DoctorSlot
from app.services.validation_service import run_all_validations
from app.services.recommendation_service import run_recommendation
from sqlalchemy import select


# =============================================
# Step 1: Search - رجّع كل الأطباء المتاحين
# =============================================
async def search_doctors(
    national_id: str,
    symptom: str,
    session: AsyncSession,
) -> dict:

    customer, policy = await run_all_validations(national_id, session)

    specialization, doctors = await run_recommendation(
        symptom=symptom,
        city=customer.city,
        package_id=policy.package_id,
        session=session,
    )

    return {
        "customer_name":  customer.name,
        "city":           customer.city,
        "specialization": specialization,
        "doctors": [
            {
                "id":             d.id,
                "name":           d.name,
                "specialization": d.specialization,
                "city":           d.city,
            }
            for d in doctors
        ],
    }


# =============================================
# Step 2: Confirm - احجز في slot معين
# =============================================
async def confirm_booking(
    national_id: str,
    doctor_id: int,
    slot_id: int,
    session: AsyncSession,
) -> dict:

    customer, policy = await run_all_validations(national_id, session)

    # تحقق إن الدكتور موجود
    result = await session.execute(
        select(Doctor).where(Doctor.id == doctor_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise ValueError("❌ الدكتور المختار غير موجود")

    # تحقق إن الـ slot موجود ومتاح
    result = await session.execute(
        select(DoctorSlot).where(
            DoctorSlot.id == slot_id,
            DoctorSlot.doctor_id == doctor_id,
            DoctorSlot.is_available == True,
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise ValueError("❌ الميعاد المختار غير متاح أو محجوز بالفعل")

    # احجز الـ slot
    slot.is_available = False

    # إنشاء الحجز
    appointment = Appointment(
        customer_id=customer.id,
        doctor_id=doctor.id,
        appointment_date=slot.slot_date,
        status="pending",
    )
    session.add(appointment)
    await session.flush()
    await session.commit()

    return {
        "appointment_id":   appointment.id,
        "customer_name":    customer.name,
        "doctor_name":      doctor.name,
        "specialization":   doctor.specialization,
        "city":             doctor.city,
        "appointment_date": slot.slot_date,
        "appointment_time": str(slot.slot_time),
        "status":           appointment.status,
    }