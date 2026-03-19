from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from app.models import Customer, Policy, Package, Appointment


# =============================================
# 1. Validate Customer by National ID
# =============================================
async def validate_customer(national_id: str, session: AsyncSession) -> Customer:
    result = await session.execute(
        select(Customer).where(Customer.national_id == national_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise ValueError(f"❌ العميل بالرقم القومي {national_id} غير موجود")

    return customer


# =============================================
# 2. Validate Active Policy
# =============================================
async def validate_policy(customer_id: int, session: AsyncSession) -> Policy:
    today = date.today()

    result = await session.execute(
        select(Policy).where(
            Policy.customer_id == customer_id,
            Policy.start_date <= today,
            Policy.end_date >= today,
        )
    )
    policy = result.scalar_one_or_none()

    if not policy:
        raise ValueError("❌ لا توجد بوليصة تأمين سارية لهذا العميل")

    return policy


# =============================================
# 3. Validate Monthly Visits Limit
# =============================================
async def validate_monthly_limit(customer_id: int, package_id: int, session: AsyncSession):
    today = date.today()

    # Get package limit
    result = await session.execute(
        select(Package).where(Package.id == package_id)
    )
    package = result.scalar_one_or_none()

    if not package:
        raise ValueError("❌ الباقة غير موجودة")

    # Count visits this month
    result = await session.execute(
        select(func.count(Appointment.id)).where(
            Appointment.customer_id == customer_id,
            func.month(Appointment.appointment_date) == today.month,
            func.year(Appointment.appointment_date) == today.year,
        )
    )
    visits_this_month = result.scalar()

    if visits_this_month >= package.max_visits_per_month:
        raise ValueError(
            f"❌ تجاوزت الحد الشهري للزيارات ({package.max_visits_per_month} زيارات/شهر)"
        )


# =============================================
# 4. Validate No Pending Appointment
# =============================================
async def validate_no_pending(customer_id: int, session: AsyncSession):
    result = await session.execute(
        select(Appointment).where(
            Appointment.customer_id == customer_id,
            Appointment.status == "pending",
        )
    )
    pending = result.scalar_one_or_none()

    if pending:
        raise ValueError("❌ يوجد حجز معلق بالفعل، لا يمكن إنشاء حجز جديد")


# =============================================
# Main Validation Runner
# =============================================
async def run_all_validations(national_id: str, session: AsyncSession):
    customer = await validate_customer(national_id, session)
    policy   = await validate_policy(customer.id, session)

    await validate_monthly_limit(customer.id, policy.package_id, session)
    await validate_no_pending(customer.id, session)

    return customer, policy