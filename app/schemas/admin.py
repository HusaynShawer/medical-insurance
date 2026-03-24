from pydantic import BaseModel
from datetime import date, time
from pydantic import BaseModel
from app.database import get_session

class SlotCreate(BaseModel):
    slot_date: date
    slot_time: time


class SlotOut(BaseModel):
    id:           int
    slot_date:    date
    slot_time:    time
    is_available: bool

    class Config:
        from_attributes = True