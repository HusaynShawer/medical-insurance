from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Literal, Optional
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

    reply, updated_history = await run_agent(
        message=body.message,
        history=history,
        session=session,
    )

    sessions[session_id] = updated_history

    return {
        "reply": reply,
        "session_id": session_id,
        "provider": "gemini",
    }

@router.delete("/{session_id}")
async def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"message": "تم مسح المحادثة"}
