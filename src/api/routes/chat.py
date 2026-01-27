import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from src.api.schemas import ChatRequest, ChatResponse
from src.api.main import get_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Procesa un mensaje y devuelve la respuesta completa."""
    agent = await get_agent()
    response = await agent.process_request(request.message, request.thread_id)
    return ChatResponse(response=response, thread_id=request.thread_id)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Procesa un mensaje y devuelve la respuesta en streaming."""

    async def event_generator():
        agent = await get_agent()
        async for event in agent.stream_request(request.message, request.thread_id):
            yield f"data: {json.dumps(event, default=str)}\n\n"
        yield "data: OK\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
