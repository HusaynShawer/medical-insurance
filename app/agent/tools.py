from google.generativeai.types import FunctionDeclaration, Tool

search_doctors_func = FunctionDeclaration(
    name="search_doctors",
    description="""ابحث عن أطباء متاحين بناءً على الرقم القومي والأعراض والمدينة.
    استخدم هذه الأداة بعد الحصول على الرقم القومي والأعراض والمدينة من العميل.
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
    استخدمها بعد أن يختار العميل دكتوراً من القائمة.""",
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

booking_tools = Tool(
    function_declarations=[
        search_doctors_func,
        get_slots_func,
        confirm_booking_func,
    ]
)
