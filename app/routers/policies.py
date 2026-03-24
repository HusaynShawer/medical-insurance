from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator, model_validator
from datetime import date
from typing import Optional
from app.database import get_session
from app.models import Policy, Customer, Package

router = APIRouter(prefix="/policies", tags=["Policies"])
from app.schemas.policies import PolicyCreate, PolicyUpdate, PolicyOut

# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
# GET /policies/
# All policies
# ─────────────────────────────────────────────

@router.get("/")
async def list_all_policies(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Policy).order_by(Policy.end_date.desc())
    )
    policies = result.scalars().all()

    today = date.today()
    enriched = []
    for p in policies:
        customer = await session.get(Customer, p.customer_id)
        package  = await session.get(Package, p.package_id)
        enriched.append({
            "id":            p.id,
            "customer_id":   p.customer_id,
            "customer_name": customer.name if customer else None,
            "national_id":   customer.national_id if customer else None,
            "package_id":    p.package_id,
            "package_name":  package.name if package else None,
            "start_date":    p.start_date,
            "end_date":      p.end_date,
            "is_active":     p.start_date <= today <= p.end_date,
        })

    return {"total": len(enriched), "policies": enriched}


# ─────────────────────────────────────────────
# GET /policies/{policy_id}
# ─────────────────────────────────────────────
@router.get("/{policy_id}")
async def get_policy(
    policy_id: int,
    session: AsyncSession = Depends(get_session),
):
    policy = await session.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=" البوليصة غير موجودة")

    today    = date.today()
    customer = await session.get(Customer, policy.customer_id)
    package  = await session.get(Package, policy.package_id)

    return {
        "id":            policy.id,
        "customer_id":   policy.customer_id,
        "customer_name": customer.name if customer else None,
        "national_id":   customer.national_id if customer else None,
        "package_id":    policy.package_id,
        "package_name":  package.name if package else None,
        "start_date":    policy.start_date,
        "end_date":      policy.end_date,
        "is_active":     policy.start_date <= today <= policy.end_date,
    }


# ─────────────────────────────────────────────
# GET /policies/customer/{national_id}
# All policies for a customer
# ─────────────────────────────────────────────
@router.get("/customer/{national_id}")
async def get_customer_policies(
    national_id: str,
    session: AsyncSession = Depends(get_session),
):
    cust_result = await session.execute(
        select(Customer).where(Customer.national_id == national_id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail=" العميل غير موجود")

    result = await session.execute(
        select(Policy)
        .where(Policy.customer_id == customer.id)
        .order_by(Policy.end_date.desc())
    )
    policies = result.scalars().all()

    today = date.today()
    enriched = []
    for p in policies:
        package = await session.get(Package, p.package_id)
        enriched.append({
            "id":           p.id,
            "package_id":   p.package_id,
            "package_name": package.name if package else None,
            "start_date":   p.start_date,
            "end_date":     p.end_date,
            "is_active":    p.start_date <= today <= p.end_date,
        })

    return {
        "customer_id":   customer.id,
        "customer_name": customer.name,
        "national_id":   customer.national_id,
        "total":         len(enriched),
        "policies":      enriched,
    }


# ─────────────────────────────────────────────
# POST /policies/
# Create a new policy for a customer
# ─────────────────────────────────────────────
@router.post("/", status_code=201)
async def create_policy(
    body: PolicyCreate,
    session: AsyncSession = Depends(get_session),
):
    # Resolve customer from national_id
    cust_result = await session.execute(
        select(Customer).where(Customer.national_id == body.national_id)
    )
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail=" العميل غير موجود")

    # Validate package exists
    package = await session.get(Package, body.package_id)
    if not package:
        raise HTTPException(status_code=404, detail=" الباقة غير موجودة")

    # Warn if there is already an active policy (don't block, just inform)
    today = date.today()
    active_result = await session.execute(
        select(Policy).where(
            Policy.customer_id == customer.id,
            Policy.start_date <= today,
            Policy.end_date >= today,
        )
    )
    existing_active = active_result.scalar_one_or_none()

    policy = Policy(
        customer_id=customer.id,
        package_id=body.package_id,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)

    response = {
        "message":       " تم إنشاء البوليصة بنجاح",
        "policy_id":     policy.id,
        "customer_name": customer.name,
        "national_id":   customer.national_id,
        "package_name":  package.name,
        "start_date":    policy.start_date,
        "end_date":      policy.end_date,
        "is_active":     policy.start_date <= today <= policy.end_date,
    }

    if existing_active:
        response["warning"] = (
            f" يوجد بوليصة نشطة بالفعل (ID: {existing_active.id}) "
            f"تنتهي في {existing_active.end_date}"
        )

    return response


# ─────────────────────────────────────────────
# PUT /policies/{policy_id}
# Update a policy's dates or package
# ─────────────────────────────────────────────

@router.put("/{policy_id}")
async def update_policy(
    policy_id: int,
    body: PolicyUpdate,
    session: AsyncSession = Depends(get_session),
):
    policy = await session.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=" البوليصة غير موجودة")

    if body.package_id is not None:
        package = await session.get(Package, body.package_id)
        if not package:
            raise HTTPException(status_code=404, detail=" الباقة غير موجودة")
        policy.package_id = body.package_id

    if body.start_date is not None: policy.start_date = body.start_date
    if body.end_date   is not None: policy.end_date   = body.end_date

    if policy.end_date <= policy.start_date:
        raise HTTPException(
            status_code=400,
            detail=" تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية",
        )

    await session.commit()
    await session.refresh(policy)

    today = date.today()
    return {
        "message":    " تم تحديث البوليصة",
        "policy_id":  policy.id,
        "package_id": policy.package_id,
        "start_date": policy.start_date,
        "end_date":   policy.end_date,
        "is_active":  policy.start_date <= today <= policy.end_date,
    }


# ─────────────────────────────────────────────
# DELETE /policies/{policy_id}
# ─────────────────────────────────────────────
@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: int,
    session: AsyncSession = Depends(get_session),
):
    policy = await session.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=" البوليصة غير موجودة")

    today = date.today()
    if policy.start_date <= today <= policy.end_date:
        raise HTTPException(
            status_code=400,
            detail=" لا يمكن حذف بوليصة نشطة — قم بتعديل تاريخ الانتهاء أولاً",
        )

    await session.delete(policy)
    await session.commit()
    return {"message": f" تم حذف البوليصة رقم {policy_id}"}