from pydantic import BaseModel
from typing import Optional
from datetime import date

class ServiceRequestBase(BaseModel):
    service_id: int
    branch_id: int
    appointment_id: int

class ServiceRequestCreate(ServiceRequestBase):
    national_id: str
    slot_id: int

class ServiceRequestOut(BaseModel):
    id: int
    request_id: int
    service_name: str
    total_cost: float
    co_payment_amount: float
    status: str
    message: str

    class Config:
        from_attributes = True

class ServiceRequestResponse(BaseModel):
    request_id: int
    service_name: str
    total_cost: float
    co_payment_amount: float
    status: str
    message: str