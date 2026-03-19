from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class SearchRequest(BaseModel):
    national_id: str
    symptom:     str

class DoctorItem(BaseModel):
    id:             int
    name:           str
    specialization: str
    city:           str

class SearchResponse(BaseModel):
    customer_name:  str
    city:           str
    specialization: str
    doctors:        list[DoctorItem]

class ConfirmRequest(BaseModel):
    national_id: str
    doctor_id:   int
    slot_id:     int

class ConfirmResponse(BaseModel):
    appointment_id:   int
    customer_name:    str
    doctor_name:      str
    specialization:   str
    city:             str
    appointment_date: date
    appointment_time: str
    status:           str