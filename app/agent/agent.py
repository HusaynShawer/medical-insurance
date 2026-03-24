from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.gemini_agent import run_agent as run_gemini
from app.agent.claude_agent import run_claude_agent

async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
    provider: str = "claude",
) -> tuple[str, list]:

    if provider == "gemini":
        return await run_gemini(message, history, session)
    return await run_claude_agent(message, history, session)
