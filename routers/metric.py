from fastapi import APIRouter
from prometheus_client import generate_latest, REGISTRY
from prometheus_client.exposition import CONTENT_TYPE_LATEST

router = APIRouter(tags=["Metric"])

@router.get("/metrics")
async def metrics():
    return generate_latest(REGISTRY), 200, {"Content-Type": CONTENT_TYPE_LATEST}