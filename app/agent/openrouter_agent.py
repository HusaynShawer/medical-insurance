"""
openrouter_agent.py — Primary agent using OpenRouter (OpenAI-compatible API).
Uses google/gemini-2.5-flash via OpenRouter.
"""

import os
import json
import inspect
import logging
import openai

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, Tuple

from app.agent.shared import (
    SYSTEM_PROMPT,
    TOOLS_SCHEMA,
    CustomJSONEncoder,
    normalize_args,
)
from app.agent.functions import TOOL_EXECUTORS

logger = logging.getLogger(__name__)

client = openai.AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL_NAME = "google/gemini-2.5-flash"
MAX_TOKENS = 1024

CARD_TOOLS = {"search_doctors", "get_slots", "get_available_services"}

OPENROUTER_TOOLS = [
    {"type": "function", "function": t}
    for t in TOOLS_SCHEMA
]


def _has_tool_calls(response) -> bool:
    return bool(
        response.choices
        and response.choices[0].message.tool_calls
    )


def _serialize_message(msg: dict) -> dict:
    out: dict = {"role": msg["role"]}
    if msg.get("content") is not None:
        out["content"] = msg["content"]
    if msg["role"] == "assistant" and msg.get("tool_calls"):
        out["tool_calls"] = msg["tool_calls"]
    if msg["role"] == "tool":
        out["tool_call_id"] = msg.get("tool_call_id")
    return out


def _serialize_history(history: list) -> list:
    return [_serialize_message(m) for m in history]


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


async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> Tuple[str, list, Optional[Any]]:
    logger.info(f"[OpenRouter] message: {message[:120]!r}")
    try:
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + _serialize_history(history)
            + [{"role": "user", "content": message}]
        )

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=OPENROUTER_TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=MAX_TOKENS,
        )

        last_tool_result: Optional[Any] = None

        while _has_tool_calls(response):
            assistant_msg = response.choices[0].message
            messages.append({
                "role":       "assistant",
                "content":    assistant_msg.content,
                "tool_calls": assistant_msg.tool_calls,
            })

            tool_responses = []
            for tc in assistant_msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                logger.info(f"[OpenRouter] → {fn_name}({fn_args})")
                result = await _execute_tool(fn_name, fn_args, session)
                logger.info(f"[OpenRouter] ← {fn_name}: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                if fn_name in CARD_TOOLS:
                    last_tool_result = result
                tool_responses.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder),
                })

            messages.extend(tool_responses)

            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=OPENROUTER_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=MAX_TOKENS,
            )

        reply = response.choices[0].message.content or ""
        updated_history = messages[1:]
        return reply, updated_history, last_tool_result

    except Exception as e:
        logger.error(f"[OpenRouter] Unexpected error: {e}", exc_info=True)
        return "عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.", history, None