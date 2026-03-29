"""
agent.py — Agent router.

Primary:  OpenRouter  (google/gemini-2.5-flash via OpenRouter)
Fallback: Claude      (set AGENT_BACKEND=claude)
Fallback: Gemini      (set AGENT_BACKEND=gemini)

All agents share the same interface:
    run_agent(message, history, session) -> (reply, history, structured_data)
"""

import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, Tuple

logger = logging.getLogger(__name__)

AGENT_BACKEND = os.getenv("AGENT_BACKEND", "openrouter").lower()


async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> Tuple[str, list, Optional[Any]]:
    """
    Single entry point for all agent backends.
    Returns: (reply_text, updated_history, structured_data_for_frontend)
    """
    if AGENT_BACKEND == "claude":
        logger.info("Using Claude agent")
        from app.agent.claude_agent import run_claude_agent
        return await run_claude_agent(message, history, session)

    elif AGENT_BACKEND == "gemini":
        logger.info("Using Gemini agent")
        from app.agent.gemini_agent import run_gemini_agent
        return await run_gemini_agent(message, history, session)

    else:
        logger.info("Using OpenRouter agent (default)")
        from app.agent.openrouter_agent import run_agent as run_openrouter
        return await run_openrouter(message, history, session)