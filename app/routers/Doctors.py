from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_session
from app.models import Doctor
from app.schemas.doctor import DoctorItem

router = APIRouter(prefix="/doctors", tags=["Doctors"])

# =============================================
# GET /doctors
# =============================================

@router.get("/", response_model=list[DoctorItem])
async def get_all_doctors(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Doctor))
    doctors = result.scalars().all()
    return doctors


# =============================================
# GET /doctors/{city}
# =============================================
@router.get("/{city}", response_model=list[DoctorItem])
async def get_doctors_by_city(
    city: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Doctor).where(Doctor.city == city)
    )
    doctors = result.scalars().all()

    if not doctors:
        raise HTTPException(status_code=404, detail=f"❌ لا يوجد أطباء في مدينة {city}")

    return doctors