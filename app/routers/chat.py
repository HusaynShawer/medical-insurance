from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Any
from app.database import get_session
from app.agent.agent import run_agent
import uuid
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat Agent"])

sessions: dict = {}

@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    session_id = body.session_id or str(uuid.uuid4())
    history = sessions.get(session_id, [])

    reply, updated_history, structured_data = await run_agent(
        message=body.message,
        history=history,
        session=session,
    )

    sessions[session_id] = updated_history

    return {
        "reply": reply,
        "session_id": session_id,
        "provider": "gemini",
        "structured_data": structured_data,
    }