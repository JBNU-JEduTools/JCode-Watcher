from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.student import router as student_router
from app.routers.assignment import router as total_router
from app.db.connection import create_db_and_tables
from app.routers.snapshot import router as snapshot_router
from app.routers.selection import router as selection_router

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # 쿠키 허용
    allow_methods=["*"],  # 모든 http 메서드 허용
    allow_headers=["*"],  # 모든 요청 헤더 허용
)

# 앱 시작 시 DB 테이블 생성
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# 라우터 포함
# app.include_router(student_router, tags=["Student"])
# app.include_router(total_router, tags=["Total"])
app.include_router(snapshot_router, tags=["Snapshot"])
app.include_router(selection_router, tags=["Selection"])