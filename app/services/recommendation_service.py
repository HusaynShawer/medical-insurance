from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Doctor, DoctorNetwork


# =============================================
# 1. Symptom → Specialization
# =============================================
SYMPTOM_MAP = {
    # Neurology
    "صداع": "Neurology",
    "headache": "Neurology",
    "دوخة": "Neurology",
    "تنميل": "Neurology",

    # Cardiology
    "ألم في الصدر": "Cardiology",
    "chest pain": "Cardiology",
    "ضيق تنفس": "Cardiology",
    "خفقان": "Cardiology",

    # Dermatology
    "مشكلة جلدية": "Dermatology",
    "skin problem": "Dermatology",
    "حكة": "Dermatology",
    "طفح جلدي": "Dermatology",
}

def classify_symptom(symptom: str) -> str:
    symptom_lower = symptom.lower().strip()

    for keyword, specialization in SYMPTOM_MAP.items():
        if keyword in symptom_lower:
            return specialization

    return "General"


# =============================================
# 2. Filter Doctors by specialization + city + network
# =============================================
async def get_recommended_doctors(
    specialization: str,
    city: str,
    package_id: int,
    session: AsyncSession,
) -> list[Doctor]:

    result = await session.execute(
        select(Doctor)
        .join(DoctorNetwork, DoctorNetwork.doctor_id == Doctor.id)
        .where(
            Doctor.specialization == specialization,
            Doctor.city == city,
            DoctorNetwork.package_id == package_id,
        )
    )
    doctors = result.scalars().all()

    return doctors


# =============================================
# Main Recommendation Runner
# =============================================
async def run_recommendation(
    symptom: str,
    city: str,
    package_id: int,
    session: AsyncSession,
):
    specialization = classify_symptom(symptom)

    doctors = await get_recommended_doctors(specialization, city, package_id, session)

    if not doctors:
        raise ValueError(
            f"❌ لا يوجد دكتور متخصص في {specialization} في مدينة {city} ضمن شبكة التأمين"
        )

    return specialization, doctors