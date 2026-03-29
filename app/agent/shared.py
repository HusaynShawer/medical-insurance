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
    normalized = CITY_ALIASES.get(city.strip().lower(), city.strip())
    return normalized


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
SERVICE TYPE DETECTION (CRITICAL)
════════════════════════════════
- If the user says "أريد أشعة", "أشعة", "radiology", "ray" → set service_type = "radiology".
- If the user says "أريد تحاليل", "تحاليل", "lab", "lab test" → set service_type = "lab_test".
- If you have already determined service_type from an earlier message, REMEMBER it. Do NOT ask again.
- When the user answers "نعم" (yes) to a question like "هل تريد أشعة؟", treat it as confirmation of the previously mentioned service_type.
- NEVER ask "هل تريد تحاليل أم أشعة؟" more than once in a conversation unless the user explicitly changes their mind.

════════════════════════════════
ADDITIONAL SERVICES SEQUENCE (STRICT)
════════════════════════════════
1. Detect service_type from user's first message (e.g., "أريد أشعة").
2. If missing, ask ONCE: "هل تريد تحاليل أم أشعة؟"
3. After receiving service_type, ask for city (if missing).
4. After receiving city, IMMEDIATELY call get_available_services with service_type and city.
5. Show results to user.
6. User selects a service and branch (by card click or text).
7. Ask for date and time.
8. Call check_service_availability.
9. If available → confirm → call request_service.
10. If not available → say "لا تتوفر مواعيد" once, then ask for different date/time.

════════════════════════════════
CITY RULES
════════════════════════════════
- Known cities: {', '.join(AVAILABLE_CITIES)}
- If the user provides a city name (e.g., "القاهرة"), use it directly.
- Do NOT ask "هل تريد أشعة؟" again after receiving the city if service_type is already known.

════════════════════════════════
PREVENT REPETITION (CRITICAL)
════════════════════════════════
- NEVER ask the same question twice in a row.
- If the user says "نعم" or "yes" to a yes/no question, move to the next step. Do NOT repeat the question.
- If you asked "هل تريد أشعة؟" and the user says "نعم", set service_type = "radiology" and proceed to ask for city or call get_available_services.

════════════════════════════════
DOCTOR BOOKING SEQUENCE
════════════════════════════════
1. Collect national_id if missing.
2. Collect symptoms if missing.
3. Call search_doctors → frontend shows doctor cards.
4. User selects a doctor.
5. Call get_slots → show real slots.
6. User selects a slot.
7. Ask confirmation: "هل تؤكد الحجز مع [doctor] في [date] [time]؟"
8. If user says "نعم" or "yes", call confirm_booking.

════════════════════════════════
GENERAL RULES
════════════════════════════════
- Keep replies short. One question at a time.
- Always respond in the user's language.
- If the user says something unrelated to current flow, assume it's a new request.
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
            "ONLY call after: user chose doctor, user chose slot from get_slots, user confirmed explicitly."
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
            "Use exact Arabic city name. service_type is REQUIRED: 'lab_test' or 'radiology'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "national_id":   {"type": "string", "description": "National ID"},
                "city":          {"type": "string", "description": "Arabic city name e.g. القاهرة"},
                "symptom":       {"type": "string", "description": "Symptoms (optional)"},
                "service_type":  {"type": "string", "description": "REQUIRED: 'lab_test' or 'radiology'"},
            },
            "required": ["national_id", "city", "service_type"],
        },
    },
    {
        "name": "check_service_availability",
        "description": (
            "Check if a service slot is available. "
            "Use service_id and branch_id from get_available_services. "
            "If not available, say so once and ask for a different date/time."
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