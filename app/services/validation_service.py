import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from app.models import Customer, Policy, Package, Appointment, ServiceRequest, Service

# Configure logger
logger = logging.getLogger(__name__)


# =============================================
# 1. Validate Customer by National ID
# =============================================
async def validate_customer(national_id: str, session: AsyncSession) -> Customer:
    """
    Validate that a customer exists with the given national ID.
    
    Args:
        national_id: Customer's national ID
        session: Database session
        
    Returns:
        Customer object if found
        
    Raises:
        ValueError: If customer not found
    """
    logger.info(f"Validating customer - national_id: {national_id}")
    
    try:
        result = await session.execute(
            select(Customer).where(Customer.national_id == national_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            logger.warning(f"Customer not found - national_id: {national_id}")
            raise ValueError(f"العميل بالرقم القومي {national_id} غير موجود")
        
        logger.info(f"Customer validated successfully - ID: {customer.id}, Name: {customer.name}, City: {customer.city}")
        return customer
        
    except ValueError as e:
        logger.warning(f"Validation error in validate_customer: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in validate_customer: {e}", exc_info=True)
        raise ValueError("An error occurred while validating customer")


# =============================================
# 2. Validate Active Policy
# =============================================
async def validate_policy(customer_id: int, session: AsyncSession) -> Policy:
    """
    Validate that the customer has an active insurance policy.
    
    Args:
        customer_id: Customer ID
        session: Database session
        
    Returns:
        Policy object if active policy found
        
    Raises:
        ValueError: If no active policy found
    """
    today = date.today()
    logger.info(f"Validating active policy - customer_id: {customer_id}, today: {today}")
    
    try:
        result = await session.execute(
            select(Policy).where(
                Policy.customer_id == customer_id,
                Policy.start_date <= today,
                Policy.end_date >= today,
            )
        )
        policy = result.scalar_one_or_none()

        if not policy:
            logger.warning(f"No active policy found for customer_id: {customer_id}")
            raise ValueError("لا توجد بوليصة تأمين سارية لهذا العميل")
        
        logger.info(f"Active policy found - ID: {policy.id}, Package ID: {policy.package_id}, "
                f"Valid from {policy.start_date} to {policy.end_date}")
        return policy
        
    except ValueError as e:
        logger.warning(f"Validation error in validate_policy: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in validate_policy: {e}", exc_info=True)
        raise ValueError("An error occurred while validating policy")


# =============================================
# 3. Validate Monthly Visits Limit
# =============================================
async def validate_monthly_limit(customer_id: int, package_id: int, session: AsyncSession):
    """
    Validate that the customer hasn't exceeded their monthly visit limit.
    
    Args:
        customer_id: Customer ID
        package_id: Insurance package ID
        session: Database session
        
    Raises:
        ValueError: If package not found or monthly limit exceeded
    """
    today = date.today()
    logger.info(f"Validating monthly limit - customer_id: {customer_id}, package_id: {package_id}, month: {today.month}/{today.year}")
    
    try:
        # Get package limit
        logger.debug(f"Fetching package details - package_id: {package_id}")
        result = await session.execute(
            select(Package).where(Package.id == package_id)
        )
        package = result.scalar_one_or_none()

        if not package:
            logger.warning(f"Package not found - package_id: {package_id}")
            raise ValueError("الباقة غير موجودة")
        
        logger.info(f"Package found - {package.name}, Max visits per month: {package.max_visits_per_month}")

        # Count visits this month
        logger.debug(f"Counting appointments for customer {customer_id} in {today.month}/{today.year}")
        result = await session.execute(
            select(func.count(Appointment.id)).where(
                Appointment.customer_id == customer_id,
                func.month(Appointment.appointment_date) == today.month,
                func.year(Appointment.appointment_date) == today.year,
            )
        )
        visits_this_month = result.scalar()
        
        logger.info(f"Customer has {visits_this_month} visits this month (limit: {package.max_visits_per_month})")

        if visits_this_month >= package.max_visits_per_month:
            logger.warning(f"Monthly limit exceeded - customer_id: {customer_id}, "
                        f"visits: {visits_this_month}, limit: {package.max_visits_per_month}")
            raise ValueError(
                f"تجاوزت الحد الشهري للزيارات ({package.max_visits_per_month} زيارات/شهر)"
            )
        
        logger.info(f"Monthly limit validation passed - {visits_this_month}/{package.max_visits_per_month} visits used")
        
    except ValueError as e:
        logger.warning(f"Validation error in validate_monthly_limit: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in validate_monthly_limit: {e}", exc_info=True)
        raise ValueError("An error occurred while validating monthly limit")


# =============================================
# 4. Validate No Pending Appointment
# =============================================
async def validate_no_pending(customer_id: int, session: AsyncSession):
    """
    Validate that the customer doesn't have any pending appointments.
    
    Args:
        customer_id: Customer ID
        session: Database session
        
    Raises:
        ValueError: If a pending appointment exists
    """
    logger.info(f"Checking for pending appointments - customer_id: {customer_id}")
    
    try:
        result = await session.execute(
            select(Appointment).where(
                Appointment.customer_id == customer_id,
                Appointment.status == "pending",
            )
        )
        pending = result.scalar_one_or_none()

        if pending:
            logger.warning(f"Found pending appointment for customer {customer_id} - appointment_id: {pending.id}")
            raise ValueError("يوجد حجز معلق بالفعل، لا يمكن إنشاء حجز جديد")
        
        logger.info(f"No pending appointments found for customer {customer_id}")
        
    except ValueError as e:
        logger.warning(f"Validation error in validate_no_pending: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in validate_no_pending: {e}", exc_info=True)
        raise ValueError("An error occurred while checking pending appointments")


# =============================================
# 5. Validate Service Limits (New)
# =============================================
async def validate_service_limits(
    customer_id: int,
    package_id: int,
    service_type: str,
    session: AsyncSession
):
    """
    Validate monthly limits for lab tests and radiology services.
    
    Args:
        customer_id: Customer ID
        package_id: Insurance package ID
        service_type: Type of service ('lab_test' or 'radiology')
        session: Database session
        
    Raises:
        ValueError: If limit is exceeded
    """
    today = date.today()
    logger.info(f"Validating service limits - customer_id: {customer_id}, service_type: {service_type}")
    
    try:
        # Get package details
        result = await session.execute(
            select(Package).where(Package.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            logger.warning(f"Package not found - package_id: {package_id}")
            return  # No limits to check if package missing
        
        # Determine max limit based on service type
        max_limit = None
        if service_type == "lab_test":
            max_limit = package.max_lab_tests_per_month
        elif service_type == "radiology":
            max_limit = package.max_radiology_per_month
        
        if max_limit is None:
            # No limit defined for this service type
            return
        
        # Count requests this month for this service type
        query = (
            select(func.count(ServiceRequest.id))
            .join(Service, ServiceRequest.service_id == Service.id)
            .where(
                ServiceRequest.customer_id == customer_id,
                Service.service_type == service_type,
                func.month(ServiceRequest.request_date) == today.month,
                func.year(ServiceRequest.request_date) == today.year,
                ServiceRequest.status.in_(["pending", "approved", "completed"])
            )
        )
        
        result = await session.execute(query)
        count = result.scalar() or 0
        
        logger.info(f"Customer has {count} {service_type} requests this month (limit: {max_limit})")
        
        if count >= max_limit:
            logger.warning(f"Service limit exceeded - customer_id: {customer_id}, "
                          f"type: {service_type}, count: {count}, limit: {max_limit}")
            raise ValueError(f"تجاوزت الحد الشهري للخدمات من نوع {service_type} ({max_limit} مرة في الشهر)")
        
        logger.info(f"Service limit validation passed - {count}/{max_limit} for {service_type}")
        
    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Error validating service limits: {e}", exc_info=True)
        raise


# =============================================
# Main Validation Runner
# =============================================
async def run_all_validations(national_id: str, session: AsyncSession):
    """
    Run all validations for a customer booking request.
    
    Validates in order:
    1. Customer exists
    2. Active insurance policy exists
    3. Monthly visit limit not exceeded
    4. No pending appointments
    
    Args:
        national_id: Customer's national ID
        session: Database session
        
    Returns:
        Tuple of (Customer, Policy) objects if all validations pass
        
    Raises:
        ValueError: If any validation fails
    """
    logger.info(f"Starting all validations for national_id: {national_id}")
    
    try:
        # Step 1: Validate customer
        logger.debug("Step 1/4: Validating customer")
        customer = await validate_customer(national_id, session)
        
        # Step 2: Validate policy
        logger.debug("Step 2/4: Validating active policy")
        policy = await validate_policy(customer.id, session)
        
        # Step 3: Validate monthly limit
        logger.debug("Step 3/4: Validating monthly visit limit")
        await validate_monthly_limit(customer.id, policy.package_id, session)
        
        # Step 4: Validate no pending appointments
        logger.debug("Step 4/4: Validating no pending appointments")
        await validate_no_pending(customer.id, session)
        
        logger.info(f"All validations passed for customer {customer.name} (ID: {customer.id})")
        return customer, policy
        
    except ValueError as e:
        logger.warning(f"Validation failed for national_id {national_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_all_validations: {e}", exc_info=True)
        raise ValueError("An error occurred while running validations")