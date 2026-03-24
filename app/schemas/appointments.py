
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
class StatusUpdate(BaseModel):
    status: str


class AppointmentOut(BaseModel):
    id:               int
    customer_id:      int
    customer_name:    Optional[str] = None
    doctor_id:        int
    doctor_name:      Optional[str] = None
    appointment_date: object
    appointment_time: Optional[str] = None
    status:           str