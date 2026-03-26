from sqlalchemy import Column, Integer, Date, String, ForeignKey
from app.models.base import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    customer_id      = Column(Integer, ForeignKey("customers.id"), nullable=False)
    doctor_id        = Column(Integer, ForeignKey("doctors.id"),   nullable=False)
    slot_id          = Column(Integer, ForeignKey("doctor_slots.id"), nullable=False)  # 🆕
    appointment_date = Column(Date, nullable=False)
    status           = Column(String(20), nullable=False, default="pending")