import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.models import Appointment, Doctor, DoctorSlot
from app.services.validation_service import run_all_validations
from app.services.recommendation_service import run_recommendation
from sqlalchemy import select

# Configure logger
logger = logging.getLogger(__name__)


# =============================================
# Step 1: Search - Return all available doctors
# =============================================
async def search_doctors(
    national_id: str,
    symptom: str,
    session: AsyncSession,
) -> dict:
    """
    Search for available doctors based on patient symptoms and insurance.
    
    Args:
        national_id: Patient's national ID
        symptom: Patient's symptoms description
        session: Database session
        
    Returns:
        Dictionary containing customer info and list of available doctors
        
    Raises:
        ValueError: If validation fails or no doctors found
    """
    logger.info(f"Searching doctors - national_id: {national_id}, symptom: {symptom[:100]}..." if len(symptom) > 100 else f"Searching doctors - national_id: {national_id}, symptom: {symptom}")
    
    try:
        # Step 1: Validate customer and insurance
        logger.debug(f"Validating customer with national_id: {national_id}")
        customer, policy = await run_all_validations(national_id, session)
        logger.info(f"Validation successful - Customer: {customer.name}, Policy package_id: {policy.package_id}")
        
        # Step 2: Get doctor recommendations based on symptoms
        logger.debug(f"Getting doctor recommendations for symptom: {symptom}, city: {customer.city}")
        specialization, doctors = await run_recommendation(
            symptom=symptom,
            city=customer.city,
            package_id=policy.package_id,
            session=session,
        )
        logger.info(f"Found {len(doctors)} doctors for specialization: {specialization}")
        
        # Log doctors found (at debug level to avoid clutter)
        if doctors:
            doctor_names = [d.name for d in doctors[:5]]  # Log first 5 doctors
            logger.debug(f"Doctors found: {doctor_names}{'...' if len(doctors) > 5 else ''}")
        
        result = {
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
        
        logger.info(f"Search completed successfully - Found {len(doctors)} doctors for patient {customer.name}")
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error in search_doctors: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in search_doctors: {e}", exc_info=True)
        raise ValueError("An error occurred while searching for doctors")


# =============================================
# Step 2: Confirm - Book a specific slot
# =============================================
async def confirm_booking(
    national_id: str,
    doctor_id: int,
    slot_id: int,
    session: AsyncSession,
) -> dict:
    """
    Confirm and create a booking for a specific doctor and time slot.
    
    Args:
        national_id: Patient's national ID
        doctor_id: Selected doctor's ID
        slot_id: Selected time slot ID
        session: Database session
        
    Returns:
        Dictionary containing appointment details
        
    Raises:
        ValueError: If validation fails, doctor not found, or slot not available
    """
    logger.info(f"Confirming booking - national_id: {national_id}, doctor_id: {doctor_id}, slot_id: {slot_id}")
    
    try:
        # Step 1: Validate customer and insurance
        logger.debug(f"Validating customer with national_id: {national_id}")
        customer, policy = await run_all_validations(national_id, session)
        logger.info(f"Validation successful - Customer: {customer.name}, Policy package_id: {policy.package_id}")
        
        # Step 2: Verify doctor exists
        logger.debug(f"Checking if doctor exists - doctor_id: {doctor_id}")
        result = await session.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            logger.warning(f"Doctor not found - doctor_id: {doctor_id}")
            raise ValueError("الدكتور المختار غير موجود")
        logger.info(f"Doctor found - {doctor.name} (specialization: {doctor.specialization})")
        
        # Step 3: Verify slot exists and is available
        logger.debug(f"Checking slot availability - slot_id: {slot_id}, doctor_id: {doctor_id}")
        result = await session.execute(
            select(DoctorSlot).where(
                DoctorSlot.id == slot_id,
                DoctorSlot.doctor_id == doctor_id,
                DoctorSlot.is_available == True,
            )
        )
        slot = result.scalar_one_or_none()
        if not slot:
            logger.warning(f"Slot not available or not found - slot_id: {slot_id}, doctor_id: {doctor_id}")
            raise ValueError("الميعاد المختار غير متاح أو محجوز بالفعل")
        logger.info(f"Slot available - Date: {slot.slot_date}, Time: {slot.slot_time}")
        
        # Step 4: Book the slot (mark as unavailable)
        logger.debug(f"Marking slot as unavailable - slot_id: {slot_id}")
        slot.is_available = False
        
        # Step 5: Create appointment record
        logger.debug(f"Creating appointment for customer {customer.id} with doctor {doctor.id}")
        appointment = Appointment(
            customer_id=customer.id,
            doctor_id=doctor.id,
            appointment_date=slot.slot_date,
            status="pending",
        )
        session.add(appointment)
        await session.flush()
        await session.commit()
        logger.info(f"Appointment created successfully - appointment_id: {appointment.id}")
        
        result = {
            "appointment_id":   appointment.id,
            "customer_name":    customer.name,
            "doctor_name":      doctor.name,
            "specialization":   doctor.specialization,
            "city":             doctor.city,
            "appointment_date": slot.slot_date,
            "appointment_time": str(slot.slot_time),
            "status":           appointment.status,
        }
        
        logger.info(f"Booking confirmed - Appointment ID: {appointment.id} for {customer.name} with Dr. {doctor.name} on {slot.slot_date} at {slot.slot_time}")
        return result
        
    except ValueError as e:
        logger.warning(f"Validation error in confirm_booking: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in confirm_booking: {e}", exc_info=True)
        await session.rollback()
        logger.info("Transaction rolled back due to error")
        raise ValueError("An error occurred while confirming the booking")