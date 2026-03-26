from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time

class BranchBase(BaseModel):
    name: str
    name_ar: str
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class BranchCreate(BranchBase):
    pass

class BranchOut(BranchBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class ServiceAvailabilityBase(BaseModel):
    branch_id: int
    service_id: int
    available_date: date
    available_time: time

class ServiceAvailabilityOut(ServiceAvailabilityBase):
    id: int
    is_available: bool
    max_capacity: int

    class Config:
        from_attributes = True

class ServiceAvailabilityCheck(BaseModel):
    service_id: int
    branch_id: int
    requested_date: date
    requested_time: str