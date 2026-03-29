from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.database import get_session
from app.models import Branch
from app.schemas.branch import BranchOut

router = APIRouter(prefix="/branches", tags=["Branches"])

@router.get("/")
async def get_all_branches(
    city: Optional[str] = Query(None, description="Filter by city"),
    session: AsyncSession = Depends(get_session)
):
    query = select(Branch).where(Branch.is_active == 1)
    if city:
        query = query.where(Branch.city == city)
    query = query.order_by(Branch.city, Branch.name_ar)
    result = await session.execute(query)
    branches = result.scalars().all()
    return branches

@router.get("/cities/")
async def get_cities(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Branch.city)
        .where(Branch.is_active == 1)
        .distinct()
        .order_by(Branch.city)
    )
    cities = [row[0] for row in result.all()]
    return {"cities": cities}

@router.get("/{branch_id}", response_model=BranchOut)
async def get_branch(
    branch_id: int,
    session: AsyncSession = Depends(get_session)
):
    branch = await session.get(Branch, branch_id)
    if not branch or not branch.is_active:
        raise HTTPException(status_code=404, detail="الفرع غير موجود")
    return branch