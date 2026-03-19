from pydantic import BaseModel, Field
from typing import Optional

class CustomerOut(BaseModel):
    id:          int
    name:        str
    national_id: str
    city:        str

    class Config:
        from_attributes = True