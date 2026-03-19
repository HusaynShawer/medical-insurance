from sqlalchemy import Column, Integer, String
from app.models.base import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(150), nullable=False, index=True)
    specialization = Column(String(100), nullable=False, index=True)
    city           = Column(String(100), nullable=False)
