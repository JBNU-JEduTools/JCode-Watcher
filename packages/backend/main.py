from contextlib import asynccontextmanager

from db.connection import check_database, create_db_and_tables
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from middleware import PrometheusMiddleware
from routers.assignment import router as assignment_router
from routers.dashboard import router as dashboard_router
from routers.log import router as log_router
from routers.metric import router as metric_router
from routers.selection import router as selection_router
from routers.snapshot import router as snapshot_router
from routers.student import router as student_router
from routers.v2 import router as v2_router
from schemas.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.AUTO_CREATE_SCHEMA:
        create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/ready")
def ready():
    try:
        check_database()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="데이터베이스 연결 실패") from exc
    return {"status": "READY"}


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # 쿠키 허용
    allow_methods=["GET", "POST"],
    allow_headers=["*"],  # 모든 요청 헤더 허용
)

app.add_middleware(PrometheusMiddleware)

# 라우터 포함
app.include_router(log_router, tags=["Log"])
app.include_router(student_router, tags=["Student"])
app.include_router(assignment_router, tags=["Assignment"])
app.include_router(snapshot_router, tags=["Snapshot"])
app.include_router(selection_router, tags=["Selection"])
app.include_router(metric_router, tags=["Metric"])
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(v2_router)
