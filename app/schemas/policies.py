from datetime import date
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional

class PolicyCreate(BaseModel):
    national_id: str           # used to look up customer
    package_id:  int
    start_date:  date
    end_date:    date

    @model_validator(mode="after")
    def validate_dates(self) -> "PolicyCreate":
        if self.end_date <= self.start_date:
            raise ValueError("تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية")
        return self


class PolicyUpdate(BaseModel):
    package_id: Optional[int]  = None
    start_date: Optional[date] = None
    end_date:   Optional[date] = None


class PolicyOut(BaseModel):
    id:           int
    customer_id:  int
    package_id:   int
    start_date:   date
    end_date:     date
    is_active:    bool

    class Config:
        from_attributes = True

