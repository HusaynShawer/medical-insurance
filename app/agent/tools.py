from google.generativeai.types import FunctionDeclaration, Tool

search_doctors_func = FunctionDeclaration(
    name="search_doctors",
    description="Search for available doctors based on national_id and symptoms. Use after obtaining national_id and symptoms. Returns list of doctors in insurance network.",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {"type": "string", "description": "14-digit national ID"},
            "symptom": {"type": "string", "description": "Symptoms or reason for visit"}
        },
        "required": ["national_id", "symptom"]
    }
)

get_slots_func = FunctionDeclaration(
    name="get_slots",
    description="Get available slots for a specific doctor. Use after user selects a doctor from search_doctors.",
    parameters={
        "type": "object",
        "properties": {
            "doctor_id": {"type": "integer", "description": "Doctor ID from search_doctors"}
        },
        "required": ["doctor_id"]
    }
)

confirm_booking_func = FunctionDeclaration(
    name="confirm_booking",
    description="Confirm booking after explicit user confirmation. Only use after user confirms doctor and slot.",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {"type": "string", "description": "National ID"},
            "doctor_id": {"type": "integer", "description": "Selected doctor ID"},
            "slot_id": {"type": "integer", "description": "Selected slot ID"}
        },
        "required": ["national_id", "doctor_id", "slot_id"]
    }
)

get_package_benefits_func = FunctionDeclaration(
    name="get_package_benefits",
    description="Get insurance package benefits including discount percentage, monthly limits, and covered services.",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {"type": "string", "description": "National ID"}
        },
        "required": ["national_id"]
    }
)

check_service_availability_func = FunctionDeclaration(
    name="check_service_availability",
    description="Check if a specific service is available at a branch on a given date and time.",
    parameters={
        "type": "object",
        "properties": {
            "service_id": {"type": "integer", "description": "Service ID from get_available_services"},
            "branch_id": {"type": "integer", "description": "Branch ID"},
            "requested_date": {"type": "string", "description": "Date in YYYY-MM-DD"},
            "requested_time": {"type": "string", "description": "Time in HH:MM:SS"}
        },
        "required": ["service_id", "branch_id", "requested_date", "requested_time"]
    }
)

request_service_func = FunctionDeclaration(
    name="request_service",
    description="Request an additional service after explicit user confirmation. Only use after check_service_availability returns available=True.",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {"type": "string", "description": "National ID"},
            "service_id": {"type": "integer", "description": "Service ID"},
            "branch_id": {"type": "integer", "description": "Branch ID"},
            "slot_id": {"type": "integer", "description": "Slot ID from check_service_availability"},
            "appointment_id": {"type": "integer", "description": "Optional: doctor appointment ID (if any)"}
        },
        "required": ["national_id", "service_id", "branch_id", "slot_id"]
    }
)

get_available_services_func = FunctionDeclaration(
    name="get_available_services",
    description="Search for available services (lab tests / radiology) based on city, national ID, and optional symptoms. Use after user chooses service type (lab_test or radiology).",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {"type": "string", "description": "National ID"},
            "city": {"type": "string", "description": "User's city"},
            "symptom": {"type": "string", "description": "Symptoms (optional)"},
            "service_type": {"type": "string", "description": "Service type: lab_test or radiology"}
        },
        "required": ["national_id", "city"]
    }
)

booking_tools = Tool(
    function_declarations=[
        search_doctors_func,
        get_slots_func,
        confirm_booking_func,
        get_package_benefits_func,
        check_service_availability_func,
        request_service_func,
        get_available_services_func,
    ]
)