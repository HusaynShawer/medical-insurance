from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_session
from app.services.service_service import (
    get_package_benefits,
    check_service_availability,
    request_service
)
from app.services.recommendation_service_v2 import get_available_services
from app.schemas.service import PackageBenefitsResponse
from app.schemas.branch import ServiceAvailabilityCheck
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestResponse

router = APIRouter(prefix="/services", tags=["Services"])


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


@router.get("/available")
async def get_available_services_endpoint(
    symptom: str,
    city: str,
    package_id: int,
    session: AsyncSession = Depends(get_session)
):
    """الحصول على الخدمات المتاحة بناءً على الأعراض والموقع"""
    try:
        result = await get_available_services(symptom, city, package_id, session)
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
            appointment_id=body.appointment_id,
            session=session
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))