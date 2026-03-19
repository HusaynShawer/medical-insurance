from pydantic import BaseModel,Field    
from typing import Optional

# =============================================
# Schema
# =============================================
class DoctorItem(BaseModel):
    id:             int
    name:           str
    specialization: str
    city:           str

    class Config:
        from_attributes = True