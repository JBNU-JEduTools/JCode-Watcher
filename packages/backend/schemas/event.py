from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventIdentityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    course_id: int = Field(gt=0)
    assignment_id: int = Field(gt=0)
    student_key: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    class_div: str = Field(min_length=1, max_length=64)
    hw_name: str = Field(min_length=1, max_length=255)
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at에는 timezone이 필요합니다.")
        return value.astimezone(timezone.utc)


class EventInsertResponse(BaseModel):
    inserted: bool
