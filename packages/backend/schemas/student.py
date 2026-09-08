from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import SQLModel
from datetime import datetime
from pydantic import Field


class SnapshotAvgResponse(BaseModel):
    snapshot_avg: Optional[int] = None
    snapshot_size_avg: Optional[float] = None

class MonitoringResponse(BaseModel):
    snapshot_avg: Optional[int] = None
    snapshot_size_avg: Optional[float] = None
    first: Optional[datetime] = None
    last: Optional[datetime] = None
    total: Optional[int] = None
    interval: Optional[int] = None

class TrendData(BaseModel):
    timestamp: str  # YYYYMMDD_HHMM 형식의 타임스탬프
    total_size: float  # 해당 시간대의 전체 코드량 (Byte)
    size_change: float  # 이전 시간대 대비 변화량 (Byte)

class GraphResponse(BaseModel):
    trends: List[TrendData]

class BuildLogResponse(BaseModel):
    binary_path: str
    cmdline: str
    exit_code: int
    cwd: str
    target_path: str
    timestamp: datetime
    file_size: int

class RunLogResponse(BaseModel):
    cmdline: str
    exit_code: int
    cwd: str
    target_path: str
    process_type: str
    timestamp: datetime
    file_size: int


class DashboardSummaryRequest(BaseModel):
    student_ids: List[int] = Field(min_length=1, max_length=500)


class DashboardStudentSummary(BaseModel):
    student_id: int
    build_count: int = 0
    build_fail_count: int = 0
    run_count: int = 0
    total_size_change: int = 0
    max_single_change: int = 0
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class DashboardSummaryResponse(BaseModel):
    students: List[DashboardStudentSummary]
