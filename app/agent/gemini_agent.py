import os
import json
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
4. اعرض القائمة بوضوح مع التخصص والمدينة لكل دكتور
5. اسأل العميل أي دكتور يفضل
6. استخدم get_slots لعرض المواعيد المتاحة للدكتور المختار
7. اسأل العميل أي موعد يناسبه
8. اطلب تأكيداً صريحاً قبل الحجز ("هل تريد تأكيد الحجز؟")
9. بعد الموافقة فقط استخدم confirm_booking

قواعد مهمة:
- تكلم بالعربية دائماً
- لا تحجز أبداً بدون موافقة صريحة من العميل
- لو مفيش أطباء في مدينة العميل، اعتذر بلطف واشرح السبب
- لو مفيش مواعيد متاحة، اقترح دكتور آخر من القائمة
- كن ودياً ومحترفاً في كل ردودك
- عرض قائمة الأطباء بشكل منظم ومرقم"""


async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        tools=[booking_tools],
        system_instruction=SYSTEM_PROMPT,
    )

    chat = model.start_chat(history=history)
    response = await chat.send_message_async(message)

    while response.candidates[0].content.parts[0].function_call.name if (
        response.candidates and
        response.candidates[0].content.parts and
        hasattr(response.candidates[0].content.parts[0], 'function_call') and
        response.candidates[0].content.parts[0].function_call.name
    ) else False:

        fn_call = response.candidates[0].content.parts[0].function_call
        fn_name = fn_call.name
        fn_args = dict(fn_call.args)

        executor = TOOL_EXECUTORS.get(fn_name)
        if not executor:
            fn_result = {"error": f"Tool {fn_name} not found"}
        else:
            import inspect
            if "session" in inspect.signature(executor).parameters:
                fn_result = await executor(**fn_args, session=session)
            else:
                fn_result = await executor(**fn_args)

        response = await chat.send_message_async(
            {
                "role": "function",
                "parts": [{
                    "function_response": {
                        "name": fn_name,
                        "response": fn_result,
                    }
                }]
            }
        )

    reply = response.text
    updated_history = chat.history

    return reply, updated_history
