import os
import inspect
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools import booking_tools
from app.agent.functions import TOOL_EXECUTORS

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """أنت مساعد حجز طبي ذكي لنظام تأمين صحي.
مهمتك مساعدة العملاء في حجز مواعيد مع الأطباء بطريقة ودية واحترافية.

اتبع هذا التسلسل دائماً:
1. اسأل عن الرقم القومي أولاً إذا لم يذكره العميل
2. اسأل عن الأعراض أو سبب الزيارة
3. استخدم search_doctors للبحث — ستحصل على قائمة أطباء
4. اعرض القائمة بوضوح مرقمة مع التخصص والمدينة لكل دكتور
5. اسأل العميل أي دكتور يفضل
6. استخدم get_slots لعرض المواعيد المتاحة للدكتور المختار
7. اسأل العميل أي موعد يناسبه
8. اطلب تأكيداً صريحاً قبل الحجز
9. بعد الموافقة فقط استخدم confirm_booking

قواعد:
- تكلم بالعربية دائماً
- لا تحجز أبداً بدون موافقة صريحة
- لو مفيش أطباء اعتذر بلطف
- لو مفيش مواعيد اقترح دكتور آخر
- كن ودياً ومحترفاً"""


def _has_function_call(response) -> bool:
    try:
        parts = response.candidates[0].content.parts
        return any(
            hasattr(p, "function_call") and p.function_call.name
            for p in parts
        )
    except (IndexError, AttributeError):
        return False


def _serialize_history(history) -> list:
    serialized = []
    for turn in history:
        parts = []
        for p in turn.parts:
            if hasattr(p, "text") and p.text:
                parts.append({"text": p.text})
        if parts:
            serialized.append({"role": turn.role, "parts": parts})
    return serialized


async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        tools=[booking_tools],
        system_instruction=SYSTEM_PROMPT,
    )

    chat = model.start_chat(history=history)
    response = await chat.send_message_async(message)

    while _has_function_call(response):
        parts = response.candidates[0].content.parts
        tool_responses = []

        for part in parts:
            if not (hasattr(part, "function_call") and part.function_call.name):
                continue

            fn_name = part.function_call.name
            fn_args = dict(part.function_call.args)
            executor = TOOL_EXECUTORS.get(fn_name)

            if not executor:
                fn_result = {"error": f"Tool {fn_name} not found"}
            elif "session" in inspect.signature(executor).parameters:
                fn_result = await executor(**fn_args, session=session)
            else:
                fn_result = await executor(**fn_args)

            tool_responses.append({
                "function_response": {
                    "name": fn_name,
                    "response": fn_result,
                }
            })

        response = await chat.send_message_async(tool_responses)

    reply = response.text
    serialized_history = _serialize_history(chat.history)

    return reply, serialized_history
