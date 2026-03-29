"""
shared.py — Single source of truth for all agents.

Contains:
- Normalization helpers (city, date, time)
- SYSTEM_PROMPT shared across all agents
- TOOLS_SCHEMA (plain dict list) used by OpenRouter & Claude directly,
  and converted to Gemini FunctionDeclaration objects in tools.py
- CustomJSONEncoder for date/time serialization
"""

import json
from datetime import date, datetime, time, timedelta

# =============================================
# City normalization
# =============================================
AVAILABLE_CITIES = [
    "القاهرة", "الإسكندرية", "الجيزة", "الأقصر",
    "أسوان", "طنطا", "المنصورة", "الإسماعيلية",
]

CITY_ALIASES: dict[str, str] = {
    # Cairo
    "cairo": "القاهرة", "al cairo": "القاهرة", "el cairo": "القاهرة",
    "القاهره": "القاهرة", "قاهرة": "القاهرة", "قاهره": "القاهرة", "القاهرة": "القاهرة",
    # Alexandria
    "alexandria": "الإسكندرية", "alex": "الإسكندرية",
    "الاسكندرية": "الإسكندرية", "اسكندرية": "الإسكندرية",
    "الإسكندريه": "الإسكندرية", "الإسكندرية": "الإسكندرية",
    # Giza
    "giza": "الجيزة", "gizah": "الجيزة",
    "الجيزه": "الجيزة", "جيزة": "الجيزة", "جيزه": "الجيزة", "الجيزة": "الجيزة",
    # Tanta
    "tanta": "طنطا", "طنطه": "طنطا", "طنطا": "طنطا",
    # Aswan
    "aswan": "أسوان", "اسوان": "أسوان", "أسوان": "أسوان",
    # Luxor
    "luxor": "الأقصر", "الاقصر": "الأقصر", "الأقصر": "الأقصر",
    # Mansoura
    "mansoura": "المنصورة", "المنصوره": "المنصورة", "المنصورة": "المنصورة",
    # Ismailia
    "ismailia": "الإسماعيلية", "الاسماعيلية": "الإسماعيلية", "الإسماعيلية": "الإسماعيلية",
}


def normalize_city(city: str) -> str:
    """Normalize city to exact DB value, or return original if unknown."""
    if not city:
        return city
    return CITY_ALIASES.get(city.strip().lower(), city.strip())


def normalize_date(raw: str) -> str:
    """
    Normalize any date string to YYYY-MM-DD (zero-padded).
    Handles: '2026-3-30', '30/3/2026', '30-3-2026', '2026/3/30'.
    Returns original string if parsing fails.
    """
    if not raw:
        return raw
    raw = raw.strip()
    normalised = raw.replace("/", "-")
    parts = normalised.split("-")
    if len(parts) == 3:
        year, month, day = (parts[0], parts[1], parts[2]) if len(parts[0]) == 4 else (parts[2], parts[1], parts[0])
        try:
            return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw


def normalize_time(raw: str) -> str:
    """
    Normalize any time string to HH:MM:SS (zero-padded, 24h).
    Handles: '9:00', '09:00', '9:00:00', '9:0:0'.
    Returns original string if parsing fails.
    """
    if not raw:
        return raw
    raw = raw.strip()
    parts = raw.split(":")
    try:
        if len(parts) == 2:
            h, m, s = parts[0], parts[1], "0"
        elif len(parts) == 3:
            h, m, s = parts
        else:
            return raw
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    except ValueError:
        return raw


def normalize_args(fn_args: dict) -> dict:
    """Apply all normalizations to a tool's argument dict."""
    args = dict(fn_args)
    if args.get("city"):
        args["city"] = normalize_city(args["city"])
    if args.get("requested_date"):
        args["requested_date"] = normalize_date(args["requested_date"])
    if args.get("requested_time"):
        args["requested_time"] = normalize_time(args["requested_time"])
    return args


# =============================================
# JSON Encoder for date/time objects
# =============================================
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime, time)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


# =============================================
# Shared system prompt
# =============================================
SYSTEM_PROMPT = f"""
You are a medical booking assistant integrated with a live database. Respond only in the user's language (Arabic or English).

════════════════════════════════
ANTI-HALLUCINATION RULES (CRITICAL)
════════════════════════════════
- NEVER invent doctor names, IDs, slot IDs, service IDs, or branch IDs.
- ONLY use IDs that were returned by a tool in this conversation.
- NEVER call confirm_booking or request_service without IDs from the tools.
- NEVER repeat a failed check_service_availability with the same date/time. Ask for a different one.
- If a tool returns an error, report it clearly and suggest the next action.

════════════════════════════════
DATE & TIME RULES (CRITICAL)
════════════════════════════════
- The user types dates and times MANUALLY — there is no working calendar widget.
- Accept any date format: "2026-3-30", "30/3/2026", "30-3-2026". The system normalizes automatically.
- Accept any time format: "9:00", "09:00", "9:00:00". The system normalizes automatically.
- Do NOT ask the user to reformat date or time input.

- NEVER call check_service_availability unless you have BOTH date AND time confirmed.
- If the user sends ONLY a time without a date → ask for the date first. Do NOT call any tool.
- If the user sends ONLY a date without a time → ask for the time. Do NOT call any tool.
- When user provides both date and time in the same message → call check_service_availability immediately.

- When check_service_availability returns not available:
  • Do NOT retry with the same date/time.
  • Say exactly: "لا تتوفر مواعيد في هذا الوقت. يرجى إدخال تاريخ أو وقت آخر."
  • Wait for the user to type a new date/time before calling the tool again.

════════════════════════════════
NEW REQUEST DETECTION (CRITICAL)
════════════════════════════════
- If the user sends a completely new request after a failed flow (e.g. "أريد تحاليل دم", "أريد حجز دكتور", "أريد أشعة"):
  • This is a FRESH start. Forget any previous failed state.
  • Do NOT respond with "لا تتوفر مواعيد" to a new service/booking request.
  • Start the correct sequence from step 1.
- The phrase "لا تتوفر مواعيد" ONLY applies when check_service_availability returned not available. Never say it for any other reason.

════════════════════════════════
CITY RULES
════════════════════════════════
- Known cities: {', '.join(AVAILABLE_CITIES)}
- The system normalizes city names automatically (English or misspelled Arabic).
- If get_available_services returns empty results, respond:
  "لم أجد خدمات في هذه المدينة. المدن المتاحة: {', '.join(AVAILABLE_CITIES)}"
  Then ask the user to choose one.

════════════════════════════════
DOCTOR BOOKING SEQUENCE
════════════════════════════════
1. Collect national_id if missing.
2. Collect symptoms if missing.
3. Call search_doctors → frontend shows doctor cards.
4. User selects a doctor (by card click or text).
5. Call get_slots → frontend shows real slot chips from DB.
6. User selects a slot.
7. Confirm: "هل تؤكد الحجز مع [doctor] في [date] [time]؟"
8. Only after explicit "نعم" or "yes": call confirm_booking.

════════════════════════════════
ADDITIONAL SERVICES SEQUENCE
════════════════════════════════
1. Ask if user wants lab tests or radiology.
2. Ask for city if missing. If user says "anywhere" or "any city", pick القاهرة as default.
3. Call get_available_services → frontend shows service cards.
4. User selects a service and branch.
5. Ask user: "يرجى إدخال التاريخ والوقت المطلوبين (مثال: 2026-03-30 09:00)"
6. Wait for user to type BOTH date and time in one message or two separate messages.
7. Once you have BOTH date and time → call check_service_availability.
8. If available → confirm with user → call request_service.
9. If NOT available → ask for a DIFFERENT date or time. Do NOT retry same values.

════════════════════════════════
GENERAL RULES
════════════════════════════════
- Keep replies short. The frontend renders cards; you only need to guide the user.
- One question at a time.
- Always respond in the user's language.
- NEVER say "لا تتوفر مواعيد" unless check_service_availability was just called and returned not available.
"""

# =============================================
# Tools schema (plain dict — used by OpenRouter & Claude)
# Gemini builds its own objects from these in tools.py
# =============================================
TOOLS_SCHEMA: list[dict] = [
    {
        "name": "search_doctors",
        "description": (
            "Search for available doctors by national_id and symptom. "
            "Returns real DB records. Call ONLY after collecting both fields."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "14-digit national ID"},
                "symptom":     {"type": "string", "description": "Symptoms or reason for visit"},
            },
            "required": ["national_id", "symptom"],
        },
    },
    {
        "name": "get_slots",
        "description": (
            "Get real available appointment slots for a doctor. "
            "Use ONLY a doctor_id returned by search_doctors in this conversation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "integer", "description": "Exact doctor_id from search_doctors result"},
            },
            "required": ["doctor_id"],
        },
    },
    {
        "name": "confirm_booking",
        "description": (
            "Confirm a doctor appointment. "
            "ONLY call after: user chose doctor, user chose slot from get_slots, user confirmed explicitly. "
            "NEVER invent doctor_id or slot_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string",  "description": "National ID"},
                "doctor_id":   {"type": "integer", "description": "doctor_id from search_doctors"},
                "slot_id":     {"type": "integer", "description": "slot_id from get_slots"},
            },
            "required": ["national_id", "doctor_id", "slot_id"],
        },
    },
    {
        "name": "get_package_benefits",
        "description": "Get insurance package benefits (discounts, limits, covered services).",
        "parameters": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "National ID"},
            },
            "required": ["national_id"],
        },
    },
    {
        "name": "get_available_services",
        "description": (
            "Search for available lab tests or radiology services in a city. "
            "Use exact Arabic city name. If empty results, ask user to choose another city."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "national_id":   {"type": "string", "description": "National ID"},
                "city":          {"type": "string", "description": "Arabic city name e.g. القاهرة"},
                "symptom":       {"type": "string", "description": "Symptoms (optional)"},
                "service_type":  {"type": "string", "description": "lab_test or radiology"},
            },
            "required": ["national_id", "city"],
        },
    },
    {
        "name": "check_service_availability",
        "description": (
            "Check if a service slot is available. "
            "Use service_id and branch_id from get_available_services. "
            "If result is not available, do NOT retry with same date/time — ask user for a different one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service_id":     {"type": "integer", "description": "service_id from get_available_services"},
                "branch_id":      {"type": "integer", "description": "branch_id from get_available_services"},
                "requested_date": {"type": "string",  "description": "Date YYYY-MM-DD"},
                "requested_time": {"type": "string",  "description": "Time HH:MM:SS"},
            },
            "required": ["service_id", "branch_id", "requested_date", "requested_time"],
        },
    },
    {
        "name": "request_service",
        "description": (
            "Book an additional service (lab test / radiology). "
            "ONLY call after check_service_availability returned available=True and user confirmed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "national_id":    {"type": "string",  "description": "National ID"},
                "service_id":     {"type": "integer", "description": "service_id from get_available_services"},
                "branch_id":      {"type": "integer", "description": "branch_id from get_available_services"},
                "slot_id":        {"type": "integer", "description": "slot_id from check_service_availability"},
                "appointment_id": {"type": "integer", "description": "Optional doctor appointment_id"},
            },
            "required": ["national_id", "service_id", "branch_id", "slot_id"],
        },
    },
]