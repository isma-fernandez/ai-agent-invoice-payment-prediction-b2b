from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request para el endpoint de chat."""
    message: str
    thread_id: str


class ChatResponse(BaseModel):
    """Response del endpoint de chat."""
    response: str
    thread_id: str
