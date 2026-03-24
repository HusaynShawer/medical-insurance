from pydantic import BaseModel, field_validator, model_validator
from datetime import date, time

class SlotOut(BaseModel):
    id:         int
    slot_date:  date
    slot_time:  time

    class Config:
        from_attributes = True

class DoctorSlotsResponse(BaseModel):
    doctor_id:       int
    doctor_name:     str
    specialization:  str
    available_slots: list[SlotOut]
