from fastapi import APIRouter, Response
from prometheus_client import generate_latest, REGISTRY
from prometheus_client.exposition import CONTENT_TYPE_LATEST

router = APIRouter(tags=["Metric"])

@router.get("/metrics")
async def metrics():
    return Response(
        generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )