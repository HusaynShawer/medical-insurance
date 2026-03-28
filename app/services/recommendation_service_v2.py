# app/services/recommendation_service_v2.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, Dict, Any
from app.models import Service, ServicePrice, Branch, ServiceAvailability
from app.models.service import ServiceType

async def get_available_services(
    symptom: str = "",
    city: str = "",
    package_id: int = None,
    service_type: Optional[str] = None,
    session: AsyncSession = None
) -> Dict[str, Any]:
    """
    Get available services based on location and service type
    
    Args:
        symptom: Patient symptoms (optional, can be empty)
        city: City name
        package_id: Insurance package ID
        service_type: Optional filter - 'lab_test' or 'radiology'
        session: Database session
    
    Returns:
        Dictionary with available branches and services
    """
    
    # First, get branches in the city
    branch_query = select(Branch).where(
        and_(
            Branch.city == city,
            Branch.is_active == 1
        )
    )
    branch_result = await session.execute(branch_query)
    branches = branch_result.scalars().all()
    
    if not branches:
        return {"message": "No branches found in this city", "available_branches": []}
    
    # Build service query with JOIN to ServicePrice
    service_query = (
        select(Service)
        .join(ServicePrice, Service.id == ServicePrice.service_id)
        .where(
            and_(
                Service.is_active == 1,
                ServicePrice.package_id == package_id,
                ServicePrice.max_visits_per_month > 0
            )
        )
    )
    
    # Filter by service type if specified
    if service_type == 'lab_test':
        service_query = service_query.where(Service.service_type == ServiceType.LAB_TEST)
    elif service_type == 'radiology':
        service_query = service_query.where(Service.service_type == ServiceType.RADIOLOGY)
    
    service_result = await session.execute(service_query)
    services = service_result.scalars().all()
    
    if not services:
        return {"message": "No services available for this package", "available_branches": []}
    
    # For each branch, get available services
    available_branches = []
    
    for branch in branches:
        branch_services = []
        
        for service in services:
            # Get service price details
            price_query = select(ServicePrice).where(
                and_(
                    ServicePrice.package_id == package_id,
                    ServicePrice.service_id == service.id
                )
            )
            price_result = await session.execute(price_query)
            service_price = price_result.scalar_one_or_none()
            
            branch_services.append({
                "service_id": service.id,
                "name": service.name_ar,
                "service_type": service.service_type.value,
                "base_price": service.base_price,
                "co_payment": service_price.co_payment if service_price else 0,
                "max_visits_per_month": service_price.max_visits_per_month if service_price else 1,
            })
        
        if branch_services:
            available_branches.append({
                "branch_id": branch.id,
                "branch_name": branch.name_ar,
                "address": branch.address,
                "city": branch.city,
                "phone": branch.phone,
                "services": branch_services
            })
    
    return {
        "city": city,
        "package_id": package_id,
        "total_branches": len(available_branches),
        "available_branches": available_branches
    }