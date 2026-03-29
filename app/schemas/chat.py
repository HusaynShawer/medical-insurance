from pydantic import BaseModel
from typing import Literal, Optional, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    provider: str
    structured_data: Optional[Any] = None