from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.agent.agent import run_agent
from app.agent.state_manager import ConversationState
from app.schemas.chat import ChatRequest, ChatResponse
import uuid

router = APIRouter(prefix="/chat", tags=["Chat Agent"])

# In-memory store for history and state
sessions: dict = {}

@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    session_id = body.session_id or str(uuid.uuid4())

    # Restore history and state
    session_data = sessions.get(session_id, {})
    history = session_data.get("history", [])
    state_dict = session_data.get("state", None)
    state = ConversationState(**state_dict) if state_dict else None

    # Run agent — now returns 4 values
    reply, updated_history, structured_data, updated_state = await run_agent(
        message=body.message,
        history=history,
        session=session,
        state=state,
    )

    # Save history and state together
    sessions[session_id] = {
        "history": updated_history,
        "state": updated_state.to_dict(),
    }

    return {
        "reply": reply,
        "session_id": session_id,
        "provider": "openrouter",
        "structured_data": structured_data,
    }