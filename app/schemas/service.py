from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time

class ServiceBase(BaseModel):
    name: str
    name_ar: str
    service_type: str
    base_price: float
    description: Optional[str] = None
    requires_doctor_approval: bool = False

class ServiceCreate(ServiceBase):
    pass

class ServiceOut(ServiceBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class ServicePriceBase(BaseModel):
    package_id: int
    service_id: int
    co_payment: float
    max_visits_per_month: int

class ServicePriceOut(ServicePriceBase):
    id: int

    class Config:
        from_attributes = True

class PackageBenefitsResponse(BaseModel):
    package_id: int
    package_name: str
    discount_percentage: float
    max_lab_tests_per_month: int
    max_radiology_per_month: int
    services: List[dict]