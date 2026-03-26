from sqlalchemy import Column, Integer, String, Float
from app.models.base import Base

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    name_ar = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    address = Column(String(300))
    phone = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    is_active = Column(Integer, default=1)