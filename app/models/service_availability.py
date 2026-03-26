from sqlalchemy import Column, Integer, ForeignKey, Date, Time, Boolean, UniqueConstraint
from app.models.base import Base

class ServiceAvailability(Base):
    __tablename__ = "service_availability"
    __table_args__ = (
        UniqueConstraint('branch_id', 'service_id', 'available_date', 'available_time', name='uq_branch_service_datetime'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    available_date = Column(Date, nullable=False)
    available_time = Column(Time, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    max_capacity = Column(Integer, default=1)