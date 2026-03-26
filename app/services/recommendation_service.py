import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Doctor, DoctorNetwork

# Configure logger
logger = logging.getLogger(__name__)


# =============================================
# 1. Symptom → Specialization Mapping
# =============================================
SYMPTOM_MAP = {
    # Neurology — Brain and Nerves
    "صداع":          "Neurology",
    "headache":      "Neurology",
    "دوخة":          "Neurology",
    "تنميل":         "Neurology",
    "مخ":            "Neurology",
    "اعصاب":         "Neurology",
    "أعصاب":         "Neurology",
    "neurology":     "Neurology",
    "رعشة":          "Neurology",
    "رعش":           "Neurology",
    "ارتجاف":        "Neurology",
    "تشنج":          "Neurology",
    "شلل":           "Neurology",
    "إغماء":         "Neurology",
    "غيبوبة":        "Neurology",
    "نوبة":          "Neurology",
    "صرع":           "Neurology",
    "ذاكرة":         "Neurology",
    "نسيان":         "Neurology",
    "ضعف في الكلام": "Neurology",
    "عدم توازن":     "Neurology",

    # Cardiology — Heart
    "ألم في الصدر":  "Cardiology",
    "chest pain":    "Cardiology",
    "ضيق تنفس":      "Cardiology",
    "خفقان":         "Cardiology",
    "قلب":           "Cardiology",
    "cardiology":    "Cardiology",
    "ضغط":           "Cardiology",
    "ذبحة":          "Cardiology",
    "أزمة قلبية":    "Cardiology",
    "تسارع القلب":   "Cardiology",

    # Dermatology — Skin
    "مشكلة جلدية":  "Dermatology",
    "skin problem":  "Dermatology",
    "حكة":           "Dermatology",
    "طفح جلدي":      "Dermatology",
    "جلدية":         "Dermatology",
    "dermatology":   "Dermatology",
    "حبوب":          "Dermatology",
    "أكزيما":        "Dermatology",
    "صدفية":         "Dermatology",
    "جرح":           "Dermatology",
    "حرق":           "Dermatology",
    "تقشر":          "Dermatology",
}


def classify_symptom(symptom: str) -> str:
    """
    Classify a symptom into a medical specialization.
    
    Args:
        symptom: The symptom description
        
    Returns:
        The matched specialization or "General" if no match found
    """
    symptom_lower = symptom.lower().strip()
    logger.debug(f"Classifying symptom: {symptom_lower}")
    
    for keyword, specialization in SYMPTOM_MAP.items():
        if keyword in symptom_lower:
            logger.info(f"Symptom '{symptom}' classified as: {specialization} (matched keyword: '{keyword}')")
            return specialization
    
    logger.info(f"No matching specialization found for symptom: '{symptom}', defaulting to 'General'")
    return "General"


# =============================================
# 2. Doctor Retrieval Logic
# =============================================
async def get_doctors(
    specialization: str,
    package_id:     int,
    session:        AsyncSession,
    city:           str | None = None,
) -> list[Doctor]:
    """
    Retrieve doctors by specialization, package, and optionally city.
    
    Args:
        specialization: Medical specialization to filter by
        package_id: Insurance package ID
        session: Database session
        city: Optional city filter
        
    Returns:
        List of Doctor objects matching the criteria
    """
    logger.info(f"Fetching doctors - specialization: {specialization}, package_id: {package_id}, city: {city}")
    
    try:
        query = (
            select(Doctor)
            .join(DoctorNetwork, DoctorNetwork.doctor_id == Doctor.id)
            .where(
                Doctor.specialization    == specialization,
                DoctorNetwork.package_id == package_id,
            )
        )
        
        if city:
            logger.debug(f"Adding city filter: {city}")
            query = query.where(Doctor.city == city)
        
        query = query.order_by(Doctor.city)
        result = await session.execute(query)
        doctors = result.scalars().all()
        
        logger.info(f"Found {len(doctors)} doctors for specialization '{specialization}' with package_id {package_id}" + 
                   (f" in city '{city}'" if city else " (no city filter)"))
        
        return doctors
        
    except Exception as e:
        logger.error(f"Error fetching doctors: {e}", exc_info=True)
        raise


# =============================================
# 3. Main Recommendation Runner
# =============================================
async def run_recommendation(
    symptom:    str,
    city:       str,
    package_id: int,
    session:    AsyncSession,
):
    """
    Run the doctor recommendation process based on symptoms.
    
    Tries to find doctors in the following order:
    1. With matched specialization and city
    2. With matched specialization, any city
    3. With General specialization and city
    4. With General specialization, any city
    
    Args:
        symptom: Patient symptoms
        city: Patient's city
        package_id: Insurance package ID
        session: Database session
        
    Returns:
        Tuple of (specialization, list of doctors)
        
    Raises:
        ValueError: If no doctors found in the insurance network
    """
    logger.info(f"Running recommendation - symptom: '{symptom}', city: '{city}', package_id: {package_id}")
    
    try:
        # Classify the symptom to get specialization
        specialization = classify_symptom(symptom)
        logger.info(f"Step 1: Symptom classified to specialization: '{specialization}'")
        
        # Step 2: Try with matched specialization and city
        logger.debug(f"Step 2a: Searching for doctors with specialization '{specialization}' in city '{city}'")
        doctors = await get_doctors(specialization, package_id, session, city=city)
        
        if doctors:
            logger.info(f"Success: Found {len(doctors)} doctors with specialization '{specialization}' in city '{city}'")
            return specialization, doctors
        
        # Step 3: Try with matched specialization, any city
        logger.info(f"Step 2b: No doctors found in city '{city}', expanding search to all cities")
        doctors = await get_doctors(specialization, package_id, session, city=None)
        
        if doctors:
            logger.info(f"Success: Found {len(doctors)} doctors with specialization '{specialization}' in any city")
            return specialization, doctors
        
        # Step 4: Try with General specialization and city
        if specialization != "General":
            logger.info(f"Step 2c: No doctors found for specialization '{specialization}', falling back to 'General' in city '{city}'")
            doctors = await get_doctors("General", package_id, session, city=city)
            
            if doctors:
                logger.info(f"Success: Found {len(doctors)} doctors with 'General' specialization in city '{city}'")
                return "General", doctors
            
            # Step 5: Try with General specialization, any city
            logger.info(f"Step 2d: No doctors found in city '{city}' for 'General', expanding search to all cities")
            doctors = await get_doctors("General", package_id, session, city=None)
            
            if doctors:
                logger.info(f"Success: Found {len(doctors)} doctors with 'General' specialization in any city")
                return "General", doctors
        
        # Step 6: No doctors found at all
        logger.error(f"No doctors found for any specialization or city with package_id {package_id}")
        raise ValueError("لا يوجد أطباء ضمن شبكة التأمين")
        
    except ValueError as e:
        # Re-raise ValueError with original message
        logger.warning(f"Recommendation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in run_recommendation: {e}", exc_info=True)
        raise ValueError("حدث خطأ أثناء البحث عن الأطباء")
    