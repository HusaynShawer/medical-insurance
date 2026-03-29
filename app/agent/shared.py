"""
shared.py — Single source of truth for all agents.
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
    "cairo": "القاهرة", "al cairo": "القاهرة", "el cairo": "القاهرة",
    "القاهره": "القاهرة", "قاهرة": "القاهرة", "قاهره": "القاهرة", "القاهرة": "القاهرة",
    "alexandria": "الإسكندرية", "alex": "الإسكندرية",
    "الاسكندرية": "الإسكندرية", "اسكندرية": "الإسكندرية",
    "الإسكندريه": "الإسكندرية", "الإسكندرية": "الإسكندرية",
    "giza": "الجيزة", "gizah": "الجيزة",
    "الجيزه": "الجيزة", "جيزة": "الجيزة", "جيزه": "الجيزة", "الجيزة": "الجيزة",
    "tanta": "طنطا", "طنطه": "طنطا", "طنطا": "طنطا",
    "aswan": "أسوان", "اسوان": "أسوان", "أسوان": "أسوان",
    "luxor": "الأقصر", "الاقصر": "الأقصر", "الأقصر": "الأقصر",
    "mansoura": "المنصورة", "المنصوره": "المنصورة", "المنصورة": "المنصورة",
    "ismailia": "الإسماعيلية", "الاسماعيلية": "الإسماعيلية", "الإسماعيلية": "الإسماعيلية",
}


def normalize_city(city: str) -> str:
    if not city:
        return city
    return CITY_ALIASES.get(city.strip().lower(), city.strip())


def normalize_date(raw: str) -> str:
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
    args = dict(fn_args)
    if args.get("city"):
        args["city"] = normalize_city(args["city"])
    if args.get("requested_date"):
        args["requested_date"] = normalize_date(args["requested_date"])
    if args.get("requested_time"):
        args["requested_time"] = normalize_time(args["requested_time"])
    return args


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime, time)):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


# =============================================
# System prompt — kept SHORT and CLEAR
# State block is injected dynamically per turn by _build_system_prompt()
# =============================================
SYSTEM_PROMPT = f"""
You are a medical booking assistant. Always respond in the user's language (Arabic or English).

════════════════════════════════
ANTI-HALLUCINATION — CRITICAL
════════════════════════════════
- NEVER invent doctor names, IDs, slot IDs, service IDs, or branch IDs.
- ONLY use IDs returned by a tool in this conversation.
- If a tool returns an error, report it and suggest next action.

════════════════════════════════
SERVICE TYPE DETECTION
════════════════════════════════
- "أشعة" / "radiology" / "ray"  → service_type = "radiology"
- "تحاليل" / "lab" / "lab test" → service_type = "lab_test"
- Ask ONCE if unclear. Never ask again after user answers.

════════════════════════════════
DOCTOR BOOKING SEQUENCE
════════════════════════════════
1. Collect national_id → collect symptom
2. Call search_doctors → show cards
3. User picks doctor → call get_slots → show slots
4. User picks slot → confirm → call confirm_booking

════════════════════════════════
SERVICE BOOKING SEQUENCE
════════════════════════════════
1. Detect service_type → collect city → call get_available_services
2. User picks service+branch → ask date & time
3. Call check_service_availability
4. If available → confirm → call request_service
5. If not → ask for different date/time (say it ONCE only)

════════════════════════════════
STRICT CONVERSATION RULES
════════════════════════════════
- One question at a time. Keep replies short.
- NEVER greet mid-conversation ("أهلاً بك" only at the very first message).
- NEVER repeat a question the user already answered.
- "نعم" / "yes" = confirmed → move to next step immediately.
- If user message starts with [اختيار الموعد] → extract date/time directly, do not ask again.
- Known cities: {', '.join(AVAILABLE_CITIES)}

════════════════════════════════
⚠️ ABSOLUTE RULE — READ LAST
════════════════════════════════
The CURRENT CONVERSATION STATE block below contains everything already collected.
Using those values directly is MANDATORY. Asking for them again is FORBIDDEN.
"""

# =============================================
# Tools schema
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