import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from sqlalchemy import select
from app.models import Doctor, DoctorSlot
from app.services.booking_service import (
    search_doctors as _search_doctors,
    confirm_booking as _confirm_booking,
)

# Configure logger
logger = logging.getLogger(__name__)


async def search_doctors(
    national_id: str,
    symptom: str,
    session: AsyncSession,
) -> dict:
    logger.info(f"Searching doctors - national_id: {national_id}, symptom: {symptom}")
    try:
        result = await _search_doctors(
            national_id=national_id,
            symptom=symptom,
            session=session,
        )
        logger.info(f"Successfully searched doctors - found {len(result.get('doctors', []))} doctors")
        return result
    except ValueError as e:
        logger.warning(f"ValueError in search_doctors: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in search_doctors: {str(e)}", exc_info=True)
        return {"error": "An unexpected error occurred"}


async def get_slots(
    doctor_id: int,
    session: AsyncSession,
) -> dict:
    logger.info(f"Fetching slots for doctor_id: {doctor_id}")
    try:
        result = await session.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            logger.warning(f"Doctor not found - doctor_id: {doctor_id}")
            return {"error": "الدكتور غير موجود"}

        today = date.today()
        logger.debug(f"Fetching available slots from {today} for doctor_id: {doctor_id}")
        
        result = await session.execute(
            select(DoctorSlot)
            .where(
                DoctorSlot.doctor_id    == doctor_id,
                DoctorSlot.slot_date    >= today,
                DoctorSlot.is_available == True,
            )
            .order_by(DoctorSlot.slot_date, DoctorSlot.slot_time)
        )
        slots = result.scalars().all()
        
        logger.info(f"Found {len(slots)} available slots for doctor {doctor.name} (id: {doctor_id})")

        if not slots:
            logger.info(f"No available slots for doctor {doctor.name} (id: {doctor_id})")
            return {
                "error":       f"لا توجد مواعيد متاحة للدكتور {doctor.name}",
                "doctor_name": doctor.name,
            }

        return {
            "doctor_id":      doctor.id,
            "doctor_name":    doctor.name,
            "specialization": doctor.specialization,
            "slots": [
                {"id": s.id, "date": str(s.slot_date), "time": str(s.slot_time)}
                for s in slots
            ],
        }
    except Exception as e:
        logger.error(f"Error fetching slots for doctor_id {doctor_id}: {str(e)}", exc_info=True)
        return {"error": "An unexpected error occurred while fetching slots"}


async def confirm_booking(
    national_id: str,
    doctor_id:   int,
    slot_id:     int,
    session: AsyncSession,
) -> dict:
    logger.info(f"Confirming booking - national_id: {national_id}, doctor_id: {doctor_id}, slot_id: {slot_id}")
    try:
        result = await _confirm_booking(
            national_id=national_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            session=session,
        )
        logger.info(f"Booking confirmed successfully - national_id: {national_id}, slot_id: {slot_id}")
        return {"success": True, **result}
    except ValueError as e:
        logger.warning(f"ValueError in confirm_booking: {str(e)} - national_id: {national_id}, slot_id: {slot_id}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in confirm_booking: {str(e)} - national_id: {national_id}, slot_id: {slot_id}", exc_info=True)
        return {"error": "An unexpected error occurred while confirming booking"}


TOOL_EXECUTORS = {
    "search_doctors":  search_doctors,
    "get_slots":       get_slots,
    "confirm_booking": confirm_booking,
}