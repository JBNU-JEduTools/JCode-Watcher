from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

# 테이블 모델
class Snapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_div: str   # 수업-분반
    hw_name: str     # 과제명
    student_id: int  # 학번
    filename: str    # 과제 코드 파일명
    timestamp: str   # 타임스탬프 - 스냅샷 파일 이름
    file_size: int   # 파일 크기