"""
agent.py — Agent router.

Primary:  OpenRouter  (google/gemini-2.5-flash via OpenRouter)
Fallback: Claude      (set AGENT_BACKEND=claude)
Fallback: Gemini      (set AGENT_BACKEND=gemini)

All agents now return: (reply, history, structured_data, state)
state must be persisted by the caller between turns.
"""

import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Any, Tuple

from app.agent.state_manager import ConversationState

logger = logging.getLogger(__name__)

AGENT_BACKEND = os.getenv("AGENT_BACKEND", "openrouter").lower()


async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
    state: Optional[ConversationState] = None,
) -> Tuple[str, list, Optional[Any], ConversationState]:
    """
    Single entry point for all agent backends.
    Returns: (reply_text, updated_history, structured_data_for_frontend, updated_state)

    IMPORTANT: Caller must persist `state` between turns and pass it back each call.
    Example in your API endpoint:
        reply, history, card_data, state = await run_agent(msg, history, session, state)
        # save history and state to your session/cache
    """
    if AGENT_BACKEND == "claude":
        logger.info("Using Claude agent")
        from app.agent.claude_agent import run_claude_agent
        return await run_claude_agent(message, history, session, state)

    elif AGENT_BACKEND == "gemini":
        logger.info("Using Gemini agent")
        from app.agent.gemini_agent import run_gemini_agent
        return await run_gemini_agent(message, history, session, state)

    else:
        logger.info("Using OpenRouter agent (default)")
        from app.agent.openrouter_agent import run_agent as run_openrouter
        return await run_openrouter(message, history, session, state)