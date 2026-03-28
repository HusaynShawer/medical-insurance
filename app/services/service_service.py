from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date
from typing import Optional, Dict, Any
from app.models import (
    Package, Service, ServicePrice, Policy, Customer,
    Branch, ServiceAvailability, ServiceRequest
)
from app.models.service_request import RequestStatus
from app.services.validation_service import validate_customer, validate_policy

# =============================================
# Get Package Benefits
# =============================================
async def get_package_benefits(
    package_id: int,
    session: AsyncSession
) -> Dict[str, Any]:
    """الحصول على مميزات الباقة والخدمات المشمولة"""
    try:
        # Get package details
        package_result = await session.execute(
            select(Package).where(Package.id == package_id)
        )
        package = package_result.scalar_one_or_none()
        if not package:
            raise ValueError("الباقة غير موجودة")

        # Get services with prices for this package
        services_query = (
            select(Service, ServicePrice)
            .join(ServicePrice, Service.id == ServicePrice.service_id)
            .where(
                and_(
                    Service.is_active == 1,
                    ServicePrice.package_id == package_id,
                    ServicePrice.max_visits_per_month > 0
                )
            )
        )
        result = await session.execute(services_query)
        services_with_prices = result.all()

        services_list = []
        for service, price in services_with_prices:
            services_list.append({
                "id": service.id,
                "name": service.name_ar,
                "service_type": service.service_type.value,
                "base_price": service.base_price,
                "co_payment": price.co_payment,
                "max_visits_per_month": price.max_visits_per_month
            })

        return {
            "package_id": package.id,
            "package_name": package.name_ar,
            "discount_percentage": package.discount_percentage,  # 🆕 من جدول packages
            "max_lab_tests_per_month": package.max_lab_tests_per_month,
            "max_radiology_per_month": package.max_radiology_per_month,
            "services": services_list
        }
    except Exception as e:
        raise e

# =============================================
# Check Service Availability
# =============================================
async def check_service_availability(
    service_id: int,
    branch_id: int,
    requested_date: date,
    requested_time: str,
    session: AsyncSession
) -> Dict[str, Any]:
    """التحقق من توفر خدمة في فرع معين"""
    try:
        # Find available slot
        slot_result = await session.execute(
            select(ServiceAvailability)
            .where(
                and_(
                    ServiceAvailability.service_id == service_id,
                    ServiceAvailability.branch_id == branch_id,
                    ServiceAvailability.available_date == requested_date,
                    ServiceAvailability.available_time == requested_time,
                    ServiceAvailability.is_available == True
                )
            )
            .limit(1)
        )
        slot = slot_result.scalar_one_or_none()

        if not slot:
            return {
                "available": False,
                "message": "لا يوجد موعد متاح في هذا التوقيت"
            }

        return {
            "available": True,
            "slot_id": slot.id,
            "message": "الموعد متاح"
        }
    except Exception as e:
        raise e

# =============================================
# Request Service
# =============================================
async def request_service(
    national_id: str,
    service_id: int,
    branch_id: int,
    slot_id: int,
    appointment_id: Optional[int] = None,   # 🆕 اختياري
    session: AsyncSession = None
) -> Dict[str, Any]:
    """طلب خدمة إضافية (تحليل/أشعة)"""
    try:
        # Validate customer
        customer = await validate_customer(national_id, session)

        # Get service details
        service_result = await session.execute(
            select(Service).where(Service.id == service_id)
        )
        service = service_result.scalar_one_or_none()
        if not service:
            raise ValueError("الخدمة غير موجودة")

        # Get branch details
        branch_result = await session.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        if not branch:
            raise ValueError("الفرع غير موجود")

        # Get slot details
        slot_result = await session.execute(
            select(ServiceAvailability).where(
                and_(
                    ServiceAvailability.id == slot_id,
                    ServiceAvailability.is_available == True
                )
            )
        )
        slot = slot_result.scalar_one_or_none()
        if not slot:
            raise ValueError("الموعد غير متاح")

        # Get policy to know package
        today = date.today()
        policy_result = await session.execute(
            select(Policy).where(
                and_(
                    Policy.customer_id == customer.id,
                    Policy.start_date <= today,
                    Policy.end_date >= today
                )
            )
        )
        policy = policy_result.scalar_one_or_none()
        if not policy:
            raise ValueError("لا توجد بوليصة تأمين نشطة")

        # Get service price for this package
        price_result = await session.execute(
            select(ServicePrice).where(
                and_(
                    ServicePrice.package_id == policy.package_id,
                    ServicePrice.service_id == service.id
                )
            )
        )
        service_price = price_result.scalar_one_or_none()
        co_payment = service_price.co_payment if service_price else 0.2

        # Calculate costs
        total_cost = service.base_price
        co_payment_amount = total_cost * co_payment

        # Create service request
        service_request = ServiceRequest(
            customer_id=customer.id,
            service_id=service.id,
            branch_id=branch.id,
            doctor_id=None,
            appointment_id=appointment_id,      # قد يكون None
            request_date=today,
            status=RequestStatus.PENDING,
            notes=f"Service requested for {slot.available_date} at {slot.available_time}",
            total_cost=total_cost,
            co_payment_amount=co_payment_amount
        )

        session.add(service_request)

        # Mark slot as booked
        slot.is_available = False

        await session.commit()
        await session.refresh(service_request)

        return {
            "request_id": service_request.id,
            "service_name": service.name_ar,
            "total_cost": total_cost,
            "co_payment_amount": co_payment_amount,
            "status": service_request.status.value,
            "message": "تم إنشاء طلب الخدمة بنجاح"
        }

    except Exception as e:
        await session.rollback()
        raise e