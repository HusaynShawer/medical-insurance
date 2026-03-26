from google.generativeai.types import FunctionDeclaration, Tool

search_doctors_func = FunctionDeclaration(
    name="search_doctors",
    description="""ابحث عن أطباء متاحين بناءً على الرقم القومي والأعراض.
    استخدم هذه الأداة بعد الحصول على الرقم القومي والأعراض من العميل.
    ترجع قائمة بكل الأطباء المتاحين في شبكة تأمين العميل.""",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {
                "type": "string",
                "description": "الرقم القومي للعميل — 14 رقم"
            },
            "symptom": {
                "type": "string",
                "description": "العرض المرضي الذي ذكره العميل — بالعربي أو الإنجليزي"
            },
        },
        "required": ["national_id", "symptom"]
    }
)

get_slots_func = FunctionDeclaration(
    name="get_slots",
    description="""اجلب المواعيد المتاحة لدكتور معين.
    استخدمها بعد أن يختار العميل دكتوراً من قائمة search_doctors.""",
    parameters={
        "type": "object",
        "properties": {
            "doctor_id": {
                "type": "integer",
                "description": "معرف الدكتور من نتيجة search_doctors"
            }
        },
        "required": ["doctor_id"]
    }
)

confirm_booking_func = FunctionDeclaration(
    name="confirm_booking",
    description="""أكد حجز الموعد بعد موافقة العميل الصريحة.
    لا تستخدم هذه الأداة إلا بعد أن يوافق العميل بوضوح على الدكتور والموعد.""",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {
                "type": "string",
                "description": "الرقم القومي للعميل"
            },
            "doctor_id": {
                "type": "integer",
                "description": "معرف الدكتور المختار"
            },
            "slot_id": {
                "type": "integer",
                "description": "معرف الموعد المختار"
            }
        },
        "required": ["national_id", "doctor_id", "slot_id"]
    }
)

# =============================================
# New Function Declarations for Additional Services
# =============================================

get_package_benefits_func = FunctionDeclaration(
    name="get_package_benefits",
    description="""الحصول على مميزات باقة التأمين الخاصة بالعميل، بما في ذلك:
    - نسبة الخصم الإجمالية للباقة
    - الحد الأقصى للتحاليل الطبية شهرياً
    - الحد الأقصى للأشعة شهرياً
    - قائمة الخدمات المشمولة (استشارات، تحاليل، أشعة) مع نسب المشاركة المالية لكل خدمة
    استخدم هذه الأداة عندما يسأل العميل عن مميزات باقة التأمين الخاصة به.""",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {
                "type": "string",
                "description": "الرقم القومي للعميل — 14 رقم"
            }
        },
        "required": ["national_id"]
    }
)

check_service_availability_func = FunctionDeclaration(
    name="check_service_availability",
    description="""التحقق من توفر خدمة معينة (تحليل/أشعة) في فرع معين في وقت محدد.
    استخدمها بعد أن يختار العميل الخدمة والفرع والموعد المطلوب.
    ترجع ما إذا كان الموعد متاحاً أم لا مع معرف الموعد إذا كان متاحاً.""",
    parameters={
        "type": "object",
        "properties": {
            "service_id": {
                "type": "integer",
                "description": "معرف الخدمة المطلوبة من نتيجة get_available_services"
            },
            "branch_id": {
                "type": "integer",
                "description": "معرف الفرع المطلوب"
            },
            "requested_date": {
                "type": "string",
                "description": "التاريخ المطلوب بصيغة YYYY-MM-DD"
            },
            "requested_time": {
                "type": "string",
                "description": "الوقت المطلوب بصيغة HH:MM:SS"
            }
        },
        "required": ["service_id", "branch_id", "requested_date", "requested_time"]
    }
)

request_service_func = FunctionDeclaration(
    name="request_service",
    description="""طلب خدمة إضافية (تحليل/أشعة/دواء) بعد موافقة العميل الصريحة.
    لا تستخدم هذه الأداة إلا بعد:
    1. أن يوافق العميل بوضوح على الخدمة والموعد
    2. أن تكون check_service_availability قد رجعت available=True
    تقوم هذه الأداة بإنشاء طلب خدمة في النظام في انتظار الموافقة.""",
    parameters={
        "type": "object",
        "properties": {
            "national_id": {
                "type": "string",
                "description": "الرقم القومي للعميل"
            },
            "service_id": {
                "type": "integer",
                "description": "معرف الخدمة المطلوبة"
            },
            "branch_id": {
                "type": "integer",
                "description": "معرف الفرع"
            },
            "slot_id": {
                "type": "integer",
                "description": "معرف الموعد من نتيجة check_service_availability"
            },
            "appointment_id": {
                "type": "integer",
                "description": "معرف الحجز الطبي الأساسي من نتيجة confirm_booking"
            }
        },
        "required": ["national_id", "service_id", "branch_id", "slot_id", "appointment_id"]
    }
)

get_available_services_func = FunctionDeclaration(
    name="get_available_services",
    description="""البحث عن خدمات متاحة (تحاليل/أشعة) بناءً على الأعراض والمدينة.
    استخدمها عندما يسأل العميل عن خدمات إضافية متاحة أو عندما تظهر الحاجة لخدمات إضافية.
    ترجع قائمة بالفروع المتاحة والخدمات المتوفرة في كل فرع.""",
    parameters={
        "type": "object",
        "properties": {
            "symptom": {
                "type": "string",
                "description": "الأعراض التي يعاني منها العميل"
            },
            "city": {
                "type": "string",
                "description": "مدينة العميل (من معلومات العميل)"
            },
            "national_id": {
                "type": "string",
                "description": "الرقم القومي للعميل (للحصول على الباقة)"
            }
        },
        "required": ["symptom", "city", "national_id"]
    }
)

# =============================================
# Tools Definition
# =============================================

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