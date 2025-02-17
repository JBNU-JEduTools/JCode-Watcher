from fastapi import APIRouter

router = APIRouter()

# 예시 라우터
# tags는 api 문서에서 api 엔드포인트 그룹화에 사용용
@router.get("/example", tags=["Example"])
def example():
    return {"message": "Hello World"}