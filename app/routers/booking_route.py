from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date
from app.database import get_session
from app.services.booking_service import search_doctors, confirm_booking
from app.schemas.booking import (
    SearchRequest,
    SearchResponse,
    ConfirmRequest,
    ConfirmResponse
)

router = APIRouter(prefix="/booking", tags=["Booking"])




# =============================================
# Step 1: POST /booking/search
# =============================================
@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await search_doctors(
            national_id=request.national_id,
            symptom=request.symptom,
            session=session,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================
# Step 2: POST /booking/confirm
# =============================================
@router.post("/confirm", response_model=ConfirmResponse)
async def confirm(
    request: ConfirmRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        result = await confirm_booking(
            national_id=request.national_id,
            doctor_id=request.doctor_id,
            slot_id=request.slot_id,
            session=session,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))