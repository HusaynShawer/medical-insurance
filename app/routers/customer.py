from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_session
from app.models import Customer
from app.schemas.customer import CustomerOut

router = APIRouter(prefix="/customers", tags=["Customers"])

# =============================================
# GET /customers
# =============================================

@router.get("/", response_model=list[CustomerOut])
async def get_all_customers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Customer))
    customers = result.scalars().all()
    return customers


# =============================================
# GET /customers/{national_id}
# =============================================
@router.get("/{national_id}", response_model=CustomerOut)
async def get_customer(
    national_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Customer).where(Customer.national_id == national_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail=f"❌ العميل غير موجود")

    return customer