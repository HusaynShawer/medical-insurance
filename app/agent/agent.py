from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.gemini_agent import run_agent as run_gemini

async def run_agent(
    message: str,
    history: list,
    session: AsyncSession,
) -> tuple[str, list]:
    return await run_gemini(message, history, session)
