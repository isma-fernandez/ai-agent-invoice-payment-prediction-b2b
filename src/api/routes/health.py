from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check del servicio."""
    return {"status": "ok", "service": "orchestrator"}
