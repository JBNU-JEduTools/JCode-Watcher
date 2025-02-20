from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.student import router as student_router
from app.routers.assignment import router as total_router
from db.connection import create_db_and_tables
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

# 아래 코드 포함 시 python main.py 로 실행 가능
# 미포함시 uvicorn 명령어로 실행 필요 - uvicorn main:app --reload --port 3000 --host 0.0.0.0
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, reload=True)