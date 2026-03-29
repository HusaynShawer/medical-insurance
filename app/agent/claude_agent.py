"""
claude_agent.py — Fallback agent using Anthropic Claude (claude-haiku-4-5).

Same features as openrouter_agent:
- Anti-hallucination system prompt (from shared.py)
- Date / time / city normalization
- Per-tool error isolation
- Structured data returned for frontend card rendering
- Returns (reply, history, last_tool_result) like all agents
"""

import os
import json
import inspect
import logging
import anthropic

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, Tuple

from app.agent.shared import (
    SYSTEM_PROMPT,
    TOOLS_SCHEMA,
    CustomJSONEncoder,
    normalize_args,
)
from app.agent.shared import TOOL_EXECUTORS

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL_NAME = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

CARD_TOOLS = {"search_doctors", "get_slots", "get_available_services"}

# Anthropic format: input_schema instead of parameters
CLAUDE_TOOLS = [
    {
        "name":         t["name"],
        "description":  t["description"],
        "input_schema": t["parameters"],
    }
    for t in TOOLS_SCHEMA
]


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


async def run_claude_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> Tuple[str, list, Optional[Any]]:
    logger.info(f"[Claude] message: {message[:120]!r}")
    try:
        history = history + [{"role": "user", "content": message}]
        last_tool_result: Optional[Any] = None

        while True:
            response = await client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=CLAUDE_TOOLS,
                messages=history,
            )

            history = history + [{"role": "assistant", "content": response.content}]

            if response.stop_reason != "tool_use":
                reply = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                return reply, history, last_tool_result

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                fn_name = block.name
                fn_args = dict(block.input)
                logger.info(f"[Claude] → {fn_name}({fn_args})")
                result = await _execute_tool(fn_name, fn_args, session)
                logger.info(f"[Claude] ← {fn_name}: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                if fn_name in CARD_TOOLS:
                    last_tool_result = result
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder),
                })

            history = history + [{"role": "user", "content": tool_results}]

    except Exception as e:
        logger.error(f"[Claude] Unexpected error: {e}", exc_info=True)
        return "عذراً، حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.", history, None