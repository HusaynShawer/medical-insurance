# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

class CustomerCreate(BaseModel):
    national_id: str
    name:        str
    phone:       Optional[str] = None
    city:        str

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 14:
            raise ValueError("الرقم القومي يجب أن يكون 14 رقماً")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("الاسم قصير جداً")
        return v


class CustomerUpdate(BaseModel):
    name:  Optional[str] = None
    phone: Optional[str] = None
    city:  Optional[str] = None


class CustomerOut(BaseModel):
    id:          int
    national_id: str
    name:        str
    phone:       Optional[str] = None
    city:        str

    class Config:
        from_attributes = True