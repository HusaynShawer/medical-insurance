from sqlalchemy import Column, Integer, ForeignKey
from app.models.base import Base

class DoctorNetwork(Base):
    __tablename__ = "doctor_network"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id  = Column(Integer, ForeignKey("doctors.id"),  nullable=False)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
