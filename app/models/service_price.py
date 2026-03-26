from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from app.models.base import Base

class ServicePrice(Base):
    __tablename__ = "service_prices"
    __table_args__ = (
        UniqueConstraint('package_id', 'service_id', name='uq_package_service'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    co_payment = Column(Float, nullable=False, default=0)  
    max_visits_per_month = Column(Integer, nullable=False, default=1)