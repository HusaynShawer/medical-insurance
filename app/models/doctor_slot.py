from sqlalchemy import Column, Integer, Date, Time, Boolean, ForeignKey
from app.models.base import Base

class DoctorSlot(Base):
    __tablename__ = "doctor_slots"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id    = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_date    = Column(Date,    nullable=False)
    slot_time    = Column(Time,    nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)