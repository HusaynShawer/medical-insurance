import os
import inspect
import logging
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools import booking_tools
from app.agent.functions import TOOL_EXECUTORS

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# System prompt in English (concise) - instructs agent to respond in user's language
SYSTEM_PROMPT = """
You are a medical booking assistant. Your only task is to execute tools and show results.

Mandatory sequence for doctor booking:
1. Ask for national_id if not provided.
2. Ask for symptoms.
3. Call search_doctors and display results exactly as returned.
4. Ask user: "Which doctor do you prefer?"
5. Call get_slots for the chosen doctor.
6. Show available slots as returned.
7. Ask user: "Which slot do you prefer?"
8. Request explicit confirmation: "Do you confirm booking with [doctor] on [slot]?"
9. After explicit confirmation, call confirm_booking.

After successful doctor booking (confirmed):
10. Ask: "Do you need any additional services? (lab tests / radiology / medicines)"
11. If yes, ask: "Do you want lab tests or radiology?"
12. Based on answer, call get_available_services with service_type="lab_test" or "radiology".
13. Display available services as returned.
14. Ask user to choose service, branch, date, and time.
15. Call check_service_availability.
16. If available, ask for explicit confirmation.
17. After confirmation, call request_service.
18. Inform user that the request is being processed.

Strict rules:
- Never invent doctor names; only use search_doctors results.
- Never use confirm_booking without doctor_id and slot_id from tools.
- Never book without explicit user confirmation.
- Always respond in the same language the user is using (Arabic or English).
- If a tool returns an error, explain the reason clearly.
"""

def _has_function_call(response) -> bool:
    try:
        parts = response.candidates[0].content.parts
        has_call = any(hasattr(p, "function_call") and p.function_call.name for p in parts)
        if has_call:
            logger.debug("Function call detected")
        return has_call
    except (IndexError, AttributeError) as e:
        logger.debug(f"No function call: {e}")
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
    logger.debug(f"Serialized {len(serialized)} turns")
    return serialized

async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:
    logger.info(f"Running agent with message: {message[:100]}...")
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[booking_tools],
            system_instruction=SYSTEM_PROMPT,
        )
        chat = model.start_chat(history=history)
        response = await chat.send_message_async(message)
        function_call_count = 0

        while _has_function_call(response):
            function_call_count += 1
            parts = response.candidates[0].content.parts
            tool_responses = []

            for part in parts:
                if not (hasattr(part, "function_call") and part.function_call.name):
                    continue
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)
                logger.info(f"Executing {fn_name} with args: {fn_args}")
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

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return "عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.", history