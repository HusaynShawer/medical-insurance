from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date
from app.database import get_session
from app.models import Customer, Policy
from app.services.recommendation_service_v2 import get_available_services
from app.schemas.branch import ServiceAvailabilityCheck
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestResponse
from app.services.service_service import (
    get_package_benefits,
    check_service_availability,
    request_service
)

router = APIRouter(prefix="/services", tags=["Services"])

@router.get("/available")
async def get_available_services_endpoint(
    city: str = Query(..., description="المدينة"),
    national_id: str = Query(..., description="الرقم القومي"),
    symptom: Optional[str] = Query(None, description="الأعراض (اختياري)"),
    service_type: Optional[str] = Query(None, description="نوع الخدمة: lab_test أو radiology"),
    session: AsyncSession = Depends(get_session)
):
    """الحصول على الخدمات المتاحة بناءً على الموقع ونوع الخدمة"""
    try:
        # Get customer
        customer_result = await session.execute(
            select(Customer).where(Customer.national_id == national_id)
        )
        customer = customer_result.scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="العميل غير موجود")

        # Get active policy
        today = date.today()
        policy_result = await session.execute(
            select(Policy)
            .where(
                Policy.customer_id == customer.id,
                Policy.start_date <= today,
                Policy.end_date >= today
            )
            .limit(1)
        )
        active_policy = policy_result.scalar_one_or_none()
        if not active_policy:
            raise HTTPException(status_code=404, detail="لا توجد بوليصة تأمين نشطة")

        result = await get_available_services(
            symptom=symptom if symptom else "",
            city=city,
            package_id=active_policy.package_id,
            service_type=service_type,
            session=session
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/package/{package_id}/benefits")
async def get_benefits(
    package_id: int,
    session: AsyncSession = Depends(get_session)
):
    """الحصول على مميزات الباقة والخدمات المشمولة"""
    try:
        result = await get_package_benefits(package_id, session)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-availability")
async def check_availability(
    body: ServiceAvailabilityCheck,
    session: AsyncSession = Depends(get_session)
):
    """التحقق من توفر خدمة في فرع معين"""
    try:
        result = await check_service_availability(
            service_id=body.service_id,
            branch_id=body.branch_id,
            requested_date=body.requested_date,
            requested_time=body.requested_time,
            session=session
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/request", response_model=ServiceRequestResponse)
async def request_service_endpoint(
    body: ServiceRequestCreate,
    session: AsyncSession = Depends(get_session)
):
    """طلب خدمة إضافية (تحليل/أشعة/دواء)"""
    try:
        result = await request_service(
            national_id=body.national_id,
            service_id=body.service_id,
            branch_id=body.branch_id,
            slot_id=body.slot_id,
            appointment_id=body.appointment_id,   # قد يكون None
            session=session
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))