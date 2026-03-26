from sqlalchemy import Column, Integer, String, Float, Boolean
from app.models.base import Base

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    name_ar = Column(String(200), nullable=False)
    active_ingredient = Column(String(200))
    category = Column(String(100))
    price = Column(Float, nullable=False)
    requires_prescription = Column(Integer, default=1)  
    is_covered = Column(Integer, default=1)