from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_session
from app.agent.agent import run_agent

router = APIRouter(prefix="/chat", tags=["Chat Agent"])

class ChatRequest(BaseModel):
    message: str
    history: list = []

class ChatResponse(BaseModel):
    reply: str
    history: list

@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    reply, updated_history = await run_agent(
        message=body.message,
        history=body.history,
        session=session,
    )

    serializable_history = []
    for turn in updated_history:
        serializable_history.append({
            "role": turn.role,
            "parts": [
                p.text if hasattr(p, "text") else str(p)
                for p in turn.parts
            ]
        })

    return {
        "reply": reply,
        "history": serializable_history,
    }
