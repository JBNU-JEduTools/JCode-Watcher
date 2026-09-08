from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardV2Request(BaseModel):
    student_keys: list[str] = Field(min_length=1, max_length=500)


class DashboardV2Student(BaseModel):
    student_key: str
    build_count: int = 0
    build_fail_count: int = 0
    run_count: int = 0
    total_size_change: int = 0
    max_single_change: int = 0
    first_activity: datetime | None = None
    last_activity: datetime | None = None


class DashboardV2Response(BaseModel):
    students: list[DashboardV2Student]


class EventPageItem(BaseModel):
    id: int
    event_id: UUID
    occurred_at: datetime
    exit_code: int
    cmdline: str
    cwd: str
    target_path: str


class EventPage(BaseModel):
    items: list[EventPageItem]
    next_cursor: str | None = None


class SnapshotPageItem(BaseModel):
    id: int
    event_id: UUID
    occurred_at: datetime
    relative_path: str
    file_size: int


class SnapshotPage(BaseModel):
    items: list[SnapshotPageItem]
    next_cursor: str | None = None
