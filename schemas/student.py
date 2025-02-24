from pydantic import BaseModel
from typing import List
from sqlmodel import SQLModel
from datetime import datetime


class SnapshotAvgResponse(BaseModel):
    snapshot_avg: int
    snapshot_size_avg: float

class SnapshotBase(SQLModel):
    class_div: str
    hw_name: str
    student_id: int
    filename: str

class SnapshotCreate(SnapshotBase):
    timestamp: datetime
    file_size: int

class SnapshotTrend(SQLModel):
    timestamp: datetime
    size: int

class GraphResponse(SQLModel):
    snapshot_trends: dict[str, List[SnapshotTrend]]