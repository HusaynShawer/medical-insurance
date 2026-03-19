from sqlalchemy import Column, Integer, String
from app.models.base import Base

class Package(Base):
    __tablename__ = "packages"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    name                 = Column(String(100), nullable=False, index=True)
    max_visits_per_month = Column(Integer, nullable=False)
