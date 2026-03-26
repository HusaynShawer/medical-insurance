from sqlalchemy import Column, Integer, String, Float
from app.models.base import Base

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    name_ar = Column(String(100), nullable=False)
    max_visits_per_month = Column(Integer, nullable=False)
    discount_percentage = Column(Float, default=0)  
    max_lab_tests_per_month = Column(Integer, default=2)  
    max_radiology_per_month = Column(Integer, default=1)  
    description = Column(String(500))