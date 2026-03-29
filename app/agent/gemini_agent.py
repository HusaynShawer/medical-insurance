"""
gemini_agent.py — Fallback agent using Google Gemini (gemini-2.5-flash).

FIXES APPLIED:
  1. Explicit ConversationState injected into every system prompt
  2. State updated after every tool call
"""

import os
import inspect
import logging
import google.generativeai as genai

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, Tuple

from app.agent.shared import SYSTEM_PROMPT, normalize_args
from app.agent.tools import booking_tools
from app.agent.functions import TOOL_EXECUTORS
from app.agent.state_manager import (
    ConversationState,
    extract_state_from_tool_result,
    update_state_from_message,
)

logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"
CARD_TOOLS = {"search_doctors", "get_slots", "get_available_services"}


def _has_function_call(response) -> bool:
    try:
        return any(
            hasattr(p, "function_call") and p.function_call.name
            for p in response.candidates[0].content.parts
        )
    except (IndexError, AttributeError):
        return False


def _serialize_history(history) -> list:
    result = []
    for turn in history:
        parts = [{"text": p.text} for p in turn.parts if hasattr(p, "text") and p.text]
        if parts:
            result.append({"role": turn.role, "parts": parts})
    return result


def _build_system_prompt(state: ConversationState) -> str:
    return SYSTEM_PROMPT + state.to_prompt_block()


async def _execute_tool(fn_name: str, fn_args: dict, session: AsyncSession) -> Any:
    fn_args = normalize_args(fn_args)
    executor = TOOL_EXECUTORS.get(fn_name)
    if not executor:
        return {"error": f"Tool '{fn_name}' not registered"}
    try:
        if "session" in inspect.signature(executor).parameters:
            return await executor(**fn_args, session=session)
        return await executor(**fn_args)
    except Exception as e:
        logger.error(f"Tool '{fn_name}' raised: {e}", exc_info=True)
        return {"error": str(e)}


async def run_gemini_agent(
    message: str,
    history: list,
    session: AsyncSession,
    state: Optional[ConversationState] = None,
) -> Tuple[str, list, Optional[Any], ConversationState]:
    if state is None:
        state = ConversationState()

    logger.info(f"[Gemini] message: {message[:120]!r}")
    state = update_state_from_message(state, message)

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            tools=[booking_tools],
            system_instruction=_build_system_prompt(state),
            generation_config={"temperature": 0.3},
        )

        chat = model.start_chat(history=history)
        response = await chat.send_message_async(message)
        last_tool_result: Optional[Any] = None

        while _has_function_call(response):
            parts = response.candidates[0].content.parts
            tool_responses = []

            for part in parts:
                if not (hasattr(part, "function_call") and part.function_call.name):
                    continue
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args)

                logger.info(f"[Gemini] → {fn_name}({fn_args})")
                result = await _execute_tool(fn_name, fn_args, session)
                logger.info(f"[Gemini] ← {fn_name}: {list(result.keys()) if isinstance(result, dict) else type(result)}")

                state = extract_state_from_tool_result(state, fn_name, fn_args, result)

                if fn_name in CARD_TOOLS:
                    last_tool_result = result

                tool_responses.append({
                    "function_response": {
                        "name":     fn_name,
                        "response": result,
                    }
                })

            response = await chat.send_message_async(tool_responses)

        reply = response.text or ""
        updated_history = _serialize_history(chat.history)
        return reply, updated_history, last_tool_result, state

    except Exception as e:
        logger.error(f"[Gemini] Unexpected error: {e}", exc_info=True)
        return "عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.", history, None, state