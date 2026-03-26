import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import date
from app.models import Service, ServicePrice, ServiceAvailability, ServiceRequest, Package, Customer, Doctor
from app.services.validation_service import validate_customer, validate_policy
from app.services.discount_service import calculate_co_payment

logger = logging.getLogger(__name__)

async def get_package_benefits(package_id: int, session: AsyncSession) -> dict:
    """الحصول على مميزات الباقة بما في ذلك الخدمات المتاحة"""
    logger.info(f"Getting package benefits for package_id: {package_id}")
    
    try:
        # Get package details
        result = await session.execute(
            select(Package).where(Package.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            raise ValueError("الباقة غير موجودة")
        
        # Get services covered by this package
        result = await session.execute(
            select(ServicePrice, Service)
            .join(Service, ServicePrice.service_id == Service.id)
            .where(ServicePrice.package_id == package_id, Service.is_active == 1)
        )
        
        services = []
        for sp, service in result:
            services.append({
                "service_id": service.id,
                "name": service.name_ar,
                "service_type": service.service_type.value,
                "co_payment": sp.co_payment,
                "max_visits_per_month": sp.max_visits_per_month
            })
        
        return {
            "package_id": package.id,
            "package_name": package.name,
            "discount_percentage": package.discount_percentage,
            "max_lab_tests_per_month": package.max_lab_tests_per_month,
            "max_radiology_per_month": package.max_radiology_per_month,
            "services": services
        }
        
    except Exception as e:
        logger.error(f"Error getting package benefits: {e}", exc_info=True)
        raise

async def check_service_availability(
    service_id: int,
    branch_id: int,
    requested_date: date,
    requested_time: str,
    session: AsyncSession
) -> dict:
    """التحقق من توفر خدمة في فرع معين في وقت محدد"""
    logger.info(f"Checking availability - service_id: {service_id}, branch_id: {branch_id}, date: {requested_date}, time: {requested_time}")
    
    try:
        # Convert time string to time object if needed
        from datetime import time
        if isinstance(requested_time, str):
            slot_time = time.fromisoformat(requested_time)
        else:
            slot_time = requested_time
        
        # Check slot availability
        result = await session.execute(
            select(ServiceAvailability)
            .where(
                ServiceAvailability.service_id == service_id,
                ServiceAvailability.branch_id == branch_id,
                ServiceAvailability.available_date == requested_date,
                ServiceAvailability.available_time == slot_time,
                ServiceAvailability.is_available == True
            )
        )
        slot = result.scalar_one_or_none()
        
        if not slot:
            return {
                "available": False,
                "message": "لا يوجد مواعيد متاحة للخدمة المطلوبة في هذا التوقيت"
            }
        
        return {
            "available": True,
            "slot_id": slot.id,
            "message": "الموعد متاح"
        }
        
    except Exception as e:
        logger.error(f"Error checking service availability: {e}", exc_info=True)
        raise

async def request_service(
    national_id: str,
    service_id: int,
    branch_id: int,
    slot_id: int,
    appointment_id: int,
    session: AsyncSession
) -> dict:
    """طلب خدمة إضافية (تحليل/أشعة/دواء)"""
    logger.info(f"Requesting service - national_id: {national_id}, service_id: {service_id}")
    
    try:
        # Validate customer
        customer = await validate_customer(national_id, session)
        
        # Validate active policy
        policy = await validate_policy(customer.id, session)
        
        # Get service details
        result = await session.execute(
            select(Service).where(Service.id == service_id, Service.is_active == 1)
        )
        service = result.scalar_one_or_none()
        
        if not service:
            raise ValueError("الخدمة غير متاحة")
        
        # Get service price for this package
        result = await session.execute(
            select(ServicePrice)
            .where(
                ServicePrice.package_id == policy.package_id,
                ServicePrice.service_id == service_id
            )
        )
        service_price = result.scalar_one_or_none()
        
        if not service_price:
            raise ValueError("هذه الخدمة غير مشمولة في باقة التأمين الخاصة بك")
        
        # Check monthly limit for this service type
        await validate_service_monthly_limit(
            customer.id,
            policy.package_id,
            service.service_type,
            session
        )
        
        # Get the slot and mark as unavailable
        result = await session.execute(
            select(ServiceAvailability).where(
                ServiceAvailability.id == slot_id,
                ServiceAvailability.is_available == True
            )
        )
        slot = result.scalar_one_or_none()
        
        if not slot:
            raise ValueError("الميعاد غير متاح")
        
        # Calculate co-payment amount
        co_payment_amount = calculate_co_payment(
            service.base_price,
            service_price.co_payment,
            policy.discount_percentage
        )
        
        # Mark slot as unavailable
        slot.is_available = False
        
        # Create service request
        service_request = ServiceRequest(
            customer_id=customer.id,
            service_id=service_id,
            branch_id=branch_id,
            appointment_id=appointment_id,
            request_date=date.today(),
            status="pending",
            total_cost=service.base_price,
            co_payment_amount=co_payment_amount
        )
        
        session.add(service_request)
        await session.commit()
        await session.refresh(service_request)
        
        logger.info(f"Service request created - request_id: {service_request.id}")
        
        return {
            "request_id": service_request.id,
            "service_name": service.name_ar,
            "total_cost": service.base_price,
            "co_payment_amount": co_payment_amount,
            "status": "pending",
            "message": "تم طلب الخدمة بنجاح، في انتظار الموافقة"
        }
        
    except Exception as e:
        logger.error(f"Error requesting service: {e}", exc_info=True)
        await session.rollback()
        raise

async def validate_service_monthly_limit(
    customer_id: int,
    package_id: int,
    service_type: str,
    session: AsyncSession
):
    """التحقق من الحد الشهري للخدمات حسب الباقة"""
    today = date.today()
    
    try:
        # Get package limits
        result = await session.execute(
            select(Package).where(Package.id == package_id)
        )
        package = result.scalar_one_or_none()
        
        if not package:
            return
        
        # Count requests this month by service type
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
        
        max_limit = None
        if service_type == "lab_test":
            max_limit = package.max_lab_tests_per_month
        elif service_type == "radiology":
            max_limit = package.max_radiology_per_month
        
        if max_limit and count >= max_limit:
            raise ValueError(f"تجاوزت الحد الشهري للخدمات من نوع {service_type} ({max_limit} مرة في الشهر)")
            
    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Error validating service limit: {e}", exc_info=True)