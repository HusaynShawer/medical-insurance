from sqlalchemy import Column, Integer, String
from app.models.base import Base

class Customer(Base):
    __tablename__ = "customers"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(150), nullable=False, index=True)
    national_id = Column(String(20), nullable=False, unique=True, index=True)
    city       = Column(String(100), nullable=False)
