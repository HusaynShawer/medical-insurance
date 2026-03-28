from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Customer
from app.schemas.customers import CustomerCreate, CustomerUpdate, CustomerOut

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("/", response_model=list[CustomerOut])
async def get_all_customers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Customer).order_by(Customer.name))
    return result.scalars().all()

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
        raise HTTPException(status_code=404, detail="العميل غير موجود")
    return customer

@router.post("/", response_model=CustomerOut, status_code=201)
async def create_customer(
    body: CustomerCreate,
    session: AsyncSession = Depends(get_session),
):
    # Check duplicate national_id
    existing = await session.execute(
        select(Customer).where(Customer.national_id == body.national_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"يوجد عميل مسجل بالفعل بالرقم القومي {body.national_id}",
        )

    customer = Customer(
        national_id=body.national_id,
        name=body.name,
        city=body.city,
        phone=body.phone,   # 🆕
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer

@router.put("/{national_id}", response_model=CustomerOut)
async def update_customer(
    national_id: str,
    body: CustomerUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Customer).where(Customer.national_id == national_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    if body.name is not None: customer.name = body.name.strip()
    if body.city is not None: customer.city = body.city.strip()
    if body.phone is not None: customer.phone = body.phone.strip()   # 🆕

    await session.commit()
    await session.refresh(customer)
    return customer

@router.delete("/{national_id}")
async def delete_customer(
    national_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Customer).where(Customer.national_id == national_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    await session.delete(customer)
    await session.commit()
    return {"message": f"تم حذف العميل {customer.name}"}