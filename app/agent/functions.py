import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from sqlalchemy import select
from app.models import Doctor, DoctorSlot
from app.services.booking_service import (
    search_doctors as _search_doctors,
    confirm_booking as _confirm_booking,
)
from app.services.service_service import (
    get_package_benefits as _get_package_benefits,
    check_service_availability as _check_availability,
    request_service as _request_service
)
from app.services.recommendation_service_v2 import get_available_services as _get_available_services
from app.services.validation_service import validate_customer, validate_policy

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


# =============================================
# New Functions for Additional Services
# =============================================

async def get_package_benefits(
    national_id: str,
    session: AsyncSession,
) -> dict:
    """الحصول على مميزات الباقة للعميل"""
    logger.info(f"Getting package benefits for national_id: {national_id}")
    try:
        customer = await validate_customer(national_id, session)
        policy = await validate_policy(customer.id, session)
        
        result = await _get_package_benefits(policy.package_id, session)
        logger.info(f"Successfully retrieved package benefits for package_id: {policy.package_id}")
        return result
    except ValueError as e:
        logger.warning(f"ValueError in get_package_benefits: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_package_benefits: {str(e)}", exc_info=True)
        return {"error": "An unexpected error occurred"}


async def check_service_availability(
    service_id: int,
    branch_id: int,
    requested_date: str,
    requested_time: str,
    session: AsyncSession,
) -> dict:
    """التحقق من توفر خدمة"""
    logger.info(f"Checking service availability - service_id: {service_id}, branch_id: {branch_id}, date: {requested_date}, time: {requested_time}")
    try:
        requested_date_obj = date.fromisoformat(requested_date)
        
        result = await _check_availability(
            service_id=service_id,
            branch_id=branch_id,
            requested_date=requested_date_obj,
            requested_time=requested_time,
            session=session
        )
        logger.info(f"Service availability check completed - available: {result.get('available', False)}")
        return result
    except ValueError as e:
        logger.warning(f"ValueError in check_service_availability: {str(e)}")
        return {"error": str(e), "available": False}
    except Exception as e:
        logger.error(f"Error in check_service_availability: {str(e)}", exc_info=True)
        return {"error": str(e), "available": False}


async def request_service(
    national_id: str,
    service_id: int,
    branch_id: int,
    slot_id: int,
    appointment_id: int,
    session: AsyncSession,
) -> dict:
    """طلب خدمة إضافية"""
    logger.info(f"Requesting service - national_id: {national_id}, service_id: {service_id}, slot_id: {slot_id}")
    try:
        result = await _request_service(
            national_id=national_id,
            service_id=service_id,
            branch_id=branch_id,
            slot_id=slot_id,
            appointment_id=appointment_id,
            session=session
        )
        logger.info(f"Service request created successfully - request_id: {result.get('request_id')}")
        return result
    except ValueError as e:
        logger.warning(f"ValueError in request_service: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in request_service: {str(e)}", exc_info=True)
        return {"error": "An unexpected error occurred"}


async def get_available_services(
    symptom: str,
    city: str,
    national_id: str,
    session: AsyncSession,
) -> dict:
    """البحث عن خدمات متاحة حسب الأعراض والموقع"""
    logger.info(f"Getting available services - symptom: {symptom}, city: {city}, national_id: {national_id}")
    try:
        customer = await validate_customer(national_id, session)
        policy = await validate_policy(customer.id, session)
        
        result = await _get_available_services(
            symptom=symptom,
            city=city,
            package_id=policy.package_id,
            session=session
        )
        logger.info(f"Found services in {len(result.get('available_branches', []))} branches")
        return result
    except ValueError as e:
        logger.warning(f"ValueError in get_available_services: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_available_services: {str(e)}", exc_info=True)
        return {"error": "An unexpected error occurred"}


# =============================================
# Tool Executors Mapping
# =============================================

TOOL_EXECUTORS = {
    "search_doctors": search_doctors,
    "get_slots": get_slots,
    "confirm_booking": confirm_booking,
    "get_package_benefits": get_package_benefits,
    "check_service_availability": check_service_availability,
    "request_service": request_service,
    "get_available_services": get_available_services,
}