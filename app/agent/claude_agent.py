import os
import inspect
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.functions import TOOL_EXECUTORS

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """أنت مساعد حجز طبي. مهمتك الوحيدة هي تنفيذ الأدوات وعرض نتائجها للعميل.

التسلسل الإلزامي:
1. اطلب الرقم القومي إذا لم يذكره العميل
2. اطلب وصف الأعراض أو سبب الزيارة
3. استدعِ search_doctors — واعرض النتيجة كما جاءت بالضبط (الاسم، التخصص، المدينة)
4. اسأل العميل: أي دكتور من القائمة تفضل؟
5. استدعِ get_slots للدكتور الذي اختاره العميل
6. اعرض المواعيد المتاحة كما جاءت من الأداة
7. اسأل العميل: أي موعد يناسبك؟
8. اطلب تأكيداً صريحاً: "هل تؤكد الحجز مع [اسم الدكتور] في [الموعد]؟"
9. بعد الموافقة الصريحة فقط استدعِ confirm_booking

قواعد صارمة — لا استثناء:
- لا تذكر أي دكتور إلا إذا جاء اسمه من نتيجة search_doctors مباشرة
- لا تقترح أي دكتور من معلوماتك الخاصة أبداً
- إذا رجعت القائمة بتخصص مختلف عما طلبه العميل، أخبره بذلك واعرض ما هو متاح فقط
- لا تستخدم confirm_booking إلا بـ doctor_id وslot_id جاءا من الأدوات فعلاً
- لا تحجز بدون موافقة صريحة من العميل
- تكلم بالعربية دائماً
- إذا رجع error من أي أداة، أخبر العميل بالسبب بوضوح"""

TOOLS = [
    {
        "name": "search_doctors",
        "description": "ابحث عن أطباء متاحين بناءً على الرقم القومي والأعراض. يرجع قائمة الأطباء المتاحين في شبكة تأمين العميل مرتبة حسب التخصص والمدينة.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "الرقم القومي 14 رقم"},
                "symptom":     {"type": "string", "description": "العرض المرضي أو سبب الزيارة"}
            },
            "required": ["national_id", "symptom"]
        }
    },
    {
        "name": "get_slots",
        "description": "اجلب المواعيد المتاحة لدكتور معين. استخدمها فقط بعد أن يختار العميل دكتوراً من قائمة search_doctors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "integer", "description": "معرف الدكتور من نتيجة search_doctors"}
            },
            "required": ["doctor_id"]
        }
    },
    {
        "name": "confirm_booking",
        "description": "أكد الحجز بعد موافقة العميل الصريحة فقط. لا تستخدم هذه الأداة إلا بعد تأكيد العميل.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "الرقم القومي للعميل"},
                "doctor_id":   {"type": "integer", "description": "معرف الدكتور المختار من get_slots"},
                "slot_id":     {"type": "integer", "description": "معرف الموعد المختار من get_slots"}
            },
            "required": ["national_id", "doctor_id", "slot_id"]
        }
    }
]


async def run_claude_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:

    history = history + [{"role": "user", "content": message}]

    while True:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        history = history + [{"role": "assistant", "content": response.content}]

        if response.stop_reason != "tool_use":
            reply = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return reply, history

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            executor = TOOL_EXECUTORS.get(block.name)
            if not executor:
                result = {"error": f"Tool {block.name} not found"}
            elif "session" in inspect.signature(executor).parameters:
                result = await executor(**block.input, session=session)
            else:
                result = await executor(**block.input)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })

        history = history + [{"role": "user", "content": tool_results}]