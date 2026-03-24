import os
import inspect
import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.functions import TOOL_EXECUTORS

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """أنت مساعد حجز طبي ذكي لنظام تأمين صحي.
مهمتك مساعدة العملاء في حجز مواعيد مع الأطباء بطريقة ودية واحترافية.
اتبع هذا التسلسل دائماً:
1. اسأل عن الرقم القومي أولاً إذا لم يذكره العميل
2. اسأل عن الأعراض أو سبب الزيارة
3. استخدم search_doctors للبحث — ستحصل على قائمة أطباء
4. اعرض القائمة بوضوح مع التخصص والمدينة لكل دكتور
5. اسأل العميل أي دكتور يفضل
6. استخدم get_slots لعرض المواعيد المتاحة للدكتور المختار
7. اسأل العميل أي موعد يناسبه
8. اطلب تأكيداً صريحاً قبل الحجز
9. بعد الموافقة فقط استخدم confirm_booking
قواعد مهمة:
- تكلم بالعربية دائماً
- لا تحجز أبداً بدون موافقة صريحة من العميل
- لو مفيش أطباء اعتذر بلطف واشرح السبب
- لو مفيش مواعيد اقترح دكتور آخر من القائمة
- كن ودياً ومحترفاً
- اعرض قائمة الأطباء بشكل منظم ومرقم"""

TOOLS = [
    {
        "name": "search_doctors",
        "description": "ابحث عن أطباء متاحين. يرجع قائمة بكل الأطباء في شبكة تأمين العميل.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string", "description": "الرقم القومي 14 رقم"},
                "symptom":     {"type": "string", "description": "العرض المرضي"}
            },
            "required": ["national_id", "symptom"]
        }
    },
    {
        "name": "get_slots",
        "description": "اجلب المواعيد المتاحة لدكتور معين.",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "integer", "description": "معرف الدكتور"}
            },
            "required": ["doctor_id"]
        }
    },
    {
        "name": "confirm_booking",
        "description": "أكد الحجز بعد موافقة العميل الصريحة فقط.",
        "input_schema": {
            "type": "object",
            "properties": {
                "national_id": {"type": "string"},
                "doctor_id":   {"type": "integer"},
                "slot_id":     {"type": "integer"}
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
