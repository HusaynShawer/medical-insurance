import os
import inspect
import logging
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools import booking_tools
from app.agent.functions import TOOL_EXECUTORS

# Configure logger
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
- لا تقترح أي دكتور من معلوماتك الخاصة أبداً حتى لو طلب العميل تخصصاً معيناً
- إذا رجعت القائمة بتخصص مختلف عما طلبه العميل، أخبره بذلك واعرض ما هو متاح فقط
- لا تستخدم confirm_booking إلا بـ doctor_id وslot_id جاءا من الأدوات فعلاً
- لا تحجز بدون موافقة صريحة من العميل
- تكلم بالعربية دائماً
- إذا رجع error من أي أداة، أخبر العميل بالسبب بوضوح"""


def _has_function_call(response) -> bool:
    """Check if the response contains a function call."""
    try:
        parts = response.candidates[0].content.parts
        has_call = any(
            hasattr(p, "function_call") and p.function_call.name
            for p in parts
        )
        if has_call:
            logger.debug("Function call detected in response")
        return has_call
    except (IndexError, AttributeError) as e:
        logger.debug(f"No function call found or error checking: {e}")
        return False


def _serialize_history(history) -> list:
    """Serialize chat history for storage."""
    serialized = []
    for turn in history:
        parts = []
        for p in turn.parts:
            if hasattr(p, "text") and p.text:
                parts.append({"text": p.text})
        if parts:
            serialized.append({"role": turn.role, "parts": parts})
    logger.debug(f"Serialized {len(serialized)} history turns")
    return serialized


async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:
    """
    Run the agent with the given message and history.
    
    Args:
        message: User message
        history: Previous conversation history
        session: Database session
    
    Returns:
        Tuple of (response text, serialized history)
    """
    logger.info(f"Running agent with message: {message[:100]}..." if len(message) > 100 else f"Running agent with message: {message}")
    logger.debug(f"History length: {len(history)}")
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[booking_tools],
            system_instruction=SYSTEM_PROMPT,
        )
        logger.debug("Gemini model initialized")

        chat = model.start_chat(history=history)
        logger.debug("Chat started with history")
        
        response = await chat.send_message_async(message)
        logger.info("Initial response received from model")
        
        function_call_count = 0
        
        while _has_function_call(response):
            function_call_count += 1
            logger.info(f"Processing function call iteration #{function_call_count}")
            
            parts = response.candidates[0].content.parts
            tool_responses = []

            for idx, part in enumerate(parts):
                if not (hasattr(part, "function_call") and part.function_call.name):
                    logger.debug(f"Part {idx}: No function call found, skipping")
                    continue

                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)
                logger.info(f"Executing function: {fn_name} with args: {fn_args}")
                
                executor = TOOL_EXECUTORS.get(fn_name)

                if not executor:
                    logger.warning(f"Tool {fn_name} not found in TOOL_EXECUTORS")
                    fn_result = {"error": f"Tool {fn_name} not found"}
                elif "session" in inspect.signature(executor).parameters:
                    logger.debug(f"Executing {fn_name} with session parameter")
                    try:
                        fn_result = await executor(**fn_args, session=session)
                        logger.info(f"Function {fn_name} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing {fn_name}: {e}", exc_info=True)
                        fn_result = {"error": f"Error executing {fn_name}: {str(e)}"}
                else:
                    logger.debug(f"Executing {fn_name} without session parameter")
                    try:
                        fn_result = await executor(**fn_args)
                        logger.info(f"Function {fn_name} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing {fn_name}: {e}", exc_info=True)
                        fn_result = {"error": f"Error executing {fn_name}: {str(e)}"}
                
                logger.debug(f"Function {fn_name} result: {fn_result}")
                tool_responses.append({
                    "function_response": {
                        "name": fn_name,
                        "response": fn_result,
                    }
                })

            logger.info(f"Sending {len(tool_responses)} tool responses back to model")
            response = await chat.send_message_async(tool_responses)
            logger.info("Received response after tool execution")

        reply = response.text
        logger.info(f"Agent response generated: {reply[:100]}..." if len(reply) > 100 else f"Agent response generated: {reply}")
        
        serialized_history = _serialize_history(chat.history)
        logger.info(f"Agent run completed - {function_call_count} function calls made")
        
        return reply, serialized_history
        
    except Exception as e:
        logger.error(f"Unexpected error in run_agent: {str(e)}", exc_info=True)
        error_message = "عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
        logger.info(f"Returning error message to user: {error_message}")
        return error_message, history