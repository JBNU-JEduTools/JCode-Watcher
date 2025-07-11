from typing import List, Dict, Union, Optional
from sqlmodel import SQLModel
from pydantic import BaseModel

class AssignmentResponse(SQLModel):
    percentile_90: Optional[float] = None
    percentile_50: Optional[float] = None
    avg_bytes: Optional[float] = None
    avg_num: Optional[float] = None
    top_7: List[Dict[str, Union[str, int, float]]] = []

class CodeSizeChange(BaseModel):
    """ 응답 모델: 학생별 코드 크기 변화량 """
    student_num: int
    size_change: float

class CodeSizeChangeResponse(BaseModel):
    """ 전체 응답 모델 (리스트 형태로 반환) """
    results: List[CodeSizeChange]

# 빌드 및 실행 평균 횟수
class BuildAvgResponse(BaseModel):
    avg_count: float

class RunAvgResponse(BaseModel):
    avg_count: float