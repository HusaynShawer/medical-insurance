import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Appointment, DoctorSlot

# Configure logger
logger = logging.getLogger(__name__)

# Define valid status transitions for appointment state machine
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
    """
    Update the status of an appointment with validation of allowed transitions.
    
    When cancelling an appointment, the associated doctor slot is automatically
    freed up (made available again).
    
    Args:
        appointment_id: ID of the appointment to update
        new_status: New status to set (pending, confirmed, completed, cancelled)
        session: Database session
        
    Returns:
        Updated Appointment object
        
    Raises:
        ValueError: If appointment not found or status transition is invalid
    """
    logger.info(f"Updating appointment status - appointment_id: {appointment_id}, new_status: {new_status}")
    
    try:
        # Retrieve the appointment
        logger.debug(f"Fetching appointment with ID: {appointment_id}")
        result = await session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            logger.warning(f"Appointment not found - appointment_id: {appointment_id}")
            raise ValueError(f"❌ الحجز رقم {appointment_id} غير موجود")
        
        logger.info(f"Current appointment status: {appointment.status} for appointment {appointment_id}")

        # Validate status transition
        allowed = VALID_TRANSITIONS.get(appointment.status, [])
        if new_status not in allowed:
            logger.warning(
                f"Invalid status transition - appointment_id: {appointment_id}, "
                f"from: {appointment.status}, to: {new_status}, allowed: {allowed}"
            )
            raise ValueError(
                f"❌ لا يمكن تغيير الحالة من '{appointment.status}' إلى '{new_status}'. "
                f"الحالات المسموحة: {allowed or ['لا يوجد — حالة نهائية']}"
            )

        # Handle cancellation: free up the associated doctor slot
        if new_status == "cancelled":
            logger.info(f"Cancelling appointment {appointment_id} - freeing up doctor slot")
            logger.debug(f"Searching for doctor slot - doctor_id: {appointment.doctor_id}, date: {appointment.appointment_date}")
            
            slot_result = await session.execute(
                select(DoctorSlot).where(
                    DoctorSlot.doctor_id == appointment.doctor_id,
                    DoctorSlot.slot_date == appointment.appointment_date,
                )
            )
            slot = slot_result.scalar_one_or_none()
            
            if slot:
                if not slot.is_available:
                    logger.info(f"Releasing slot {slot.id} - was previously booked")
                    slot.is_available = True
                else:
                    logger.warning(f"Slot {slot.id} was already available - inconsistent state")
            else:
                logger.warning(f"No doctor slot found for appointment {appointment_id} - doctor_id: {appointment.doctor_id}, date: {appointment.appointment_date}")

        # Update and commit the status change
        old_status = appointment.status
        appointment.status = new_status
        await session.commit()
        await session.refresh(appointment)
        
        logger.info(
            f"Appointment status updated successfully - appointment_id: {appointment_id}, "
            f"status changed from '{old_status}' to '{new_status}'"
        )
        
        return appointment
        
    except ValueError as e:
        logger.warning(f"Validation error in update_appointment_status: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in update_appointment_status: {e}", exc_info=True)
        await session.rollback()
        raise ValueError(f"An error occurred while updating appointment status: {str(e)}")


async def get_appointment(
    appointment_id: int,
    session: AsyncSession,
) -> Appointment:
    """
    Retrieve a single appointment by ID.
    
    Args:
        appointment_id: ID of the appointment to retrieve
        session: Database session
        
    Returns:
        Appointment object
        
    Raises:
        ValueError: If appointment not found
    """
    logger.info(f"Fetching appointment details - appointment_id: {appointment_id}")
    
    try:
        result = await session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            logger.warning(f"Appointment not found - appointment_id: {appointment_id}")
            raise ValueError(f" الحجز رقم {appointment_id} غير موجود")
        
        logger.info(f"Appointment found - ID: {appointment_id}, Status: {appointment.status}, "
                   f"Customer: {appointment.customer_id}, Doctor: {appointment.doctor_id}")
        
        return appointment
        
    except ValueError as e:
        logger.warning(f"Error in get_appointment: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_appointment: {e}", exc_info=True)
        raise ValueError(f"An error occurred while retrieving appointment: {str(e)}")


async def get_all_appointments(session: AsyncSession) -> list[Appointment]:
    """
    Retrieve all appointments from the database.
    
    Args:
        session: Database session
        
    Returns:
        List of all Appointment objects
    """
    logger.info("Fetching all appointments")
    
    try:
        result = await session.execute(select(Appointment))
        appointments = result.scalars().all()
        
        logger.info(f"Retrieved {len(appointments)} appointments from database")
        
        # Log status breakdown at debug level for monitoring
        if appointments:
            status_counts = {}
            for app in appointments:
                status_counts[app.status] = status_counts.get(app.status, 0) + 1
            logger.debug(f"Appointment status breakdown: {status_counts}")
        
        return appointments
        
    except Exception as e:
        logger.error(f"Error fetching all appointments: {e}", exc_info=True)
        raise ValueError(f"An error occurred while retrieving appointments: {str(e)}")