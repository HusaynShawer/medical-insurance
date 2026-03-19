from sqlalchemy import Column, Integer, Date, ForeignKey
from app.models.base import Base

class Policy(Base):
    __tablename__ = "policies"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    package_id  = Column(Integer, ForeignKey("packages.id"),  nullable=False)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)
