from sqlalchemy import Column, Integer, String, Float, Enum
from app.models.base import Base
import enum

class ServiceType(str, enum.Enum):
    CONSULTATION = "consultation"      
    LAB_TEST = "lab_test"              
    RADIOLOGY = "radiology"           
    MEDICINE = "medicine"              

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    name_ar = Column(String(200), nullable=False)
    service_type = Column(Enum(ServiceType), nullable=False, index=True)
    base_price = Column(Float, nullable=False)
    description = Column(String(500))
    requires_doctor_approval = Column(Integer, default=0)  
    is_active = Column(Integer, default=1)