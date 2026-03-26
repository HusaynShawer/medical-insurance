import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import Service, ServiceAvailability, Branch
from datetime import date

logger = logging.getLogger(__name__)

# Symptom to service mapping
SYMPTOM_SERVICE_MAP = {
    "صداع": ["consultation", "radiology"],
    "headache": ["consultation", "radiology"],
    "سكر": ["consultation", "lab_test"],
    "diabetes": ["consultation", "lab_test"],
    "ضغط": ["consultation", "lab_test"],
    "blood pressure": ["consultation", "lab_test"],
    "كحة": ["consultation", "radiology"],
    "cough": ["consultation", "radiology"],
    "حرارة": ["consultation", "lab_test"],
    "fever": ["consultation", "lab_test"],
}

async def get_available_services(
    symptom: str,
    city: str,
    package_id: int,
    session: AsyncSession
) -> dict:
    """الحصول على الخدمات المتاحة بناءً على الأعراض والموقع"""
    logger.info(f"Getting available services - symptom: {symptom}, city: {city}")
    
    try:
        symptom_lower = symptom.lower()
        
        # Determine suggested service types based on symptom
        suggested_types = ["consultation"]  # consultation is always included
        for keyword, types in SYMPTOM_SERVICE_MAP.items():
            if keyword in symptom_lower:
                suggested_types.extend(types)
        
        suggested_types = list(set(suggested_types))
        
        # Get branches in city
        result = await session.execute(
            select(Branch).where(Branch.city == city, Branch.is_active == 1)
        )
        branches = result.scalars().all()
        
        if not branches:
            raise ValueError(f"لا توجد فروع في مدينة {city}")
        
        # Get available services
        today = date.today()
        services_by_branch = []
        
        for branch in branches:
            # Get services available at this branch
            result = await session.execute(
                select(Service, ServiceAvailability)
                .join(ServiceAvailability, Service.id == ServiceAvailability.service_id)
                .where(
                    ServiceAvailability.branch_id == branch.id,
                    ServiceAvailability.available_date >= today,
                    ServiceAvailability.is_available == True,
                    Service.is_active == 1
                )
                .distinct()
            )
            
            services = []
            for service, _ in result:
                if service.service_type.value in suggested_types or service.service_type.value == "consultation":
                    services.append({
                        "service_id": service.id,
                        "name": service.name_ar,
                        "service_type": service.service_type.value,
                        "base_price": service.base_price
                    })
            
            if services:
                services_by_branch.append({
                    "branch_id": branch.id,
                    "branch_name": branch.name_ar,
                    "address": branch.address,
                    "services": services
                })
        
        return {
            "symptom": symptom,
            "city": city,
            "suggested_service_types": suggested_types,
            "available_branches": services_by_branch
        }
        
    except Exception as e:
        logger.error(f"Error getting available services: {e}", exc_info=True)
        raise