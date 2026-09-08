from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Integer, String, Uuid, func
from sqlmodel import Field, SQLModel

identity_column = BigInteger().with_variant(Integer, "sqlite")


class EventIdentity(SQLModel):
    id: int | None = Field(default=None, primary_key=True, sa_type=identity_column)
    event_id: UUID = Field(unique=True, nullable=False, sa_type=Uuid(as_uuid=True))
    course_id: int = Field(nullable=False, sa_type=BigInteger)
    assignment_id: int = Field(nullable=False, sa_type=BigInteger)
    student_key: str = Field(nullable=False, sa_type=String(32))
    class_div: str = Field(nullable=False, sa_type=String(64))
    hw_name: str = Field(nullable=False, sa_type=String(255))
    occurred_at: datetime = Field(nullable=False, sa_type=DateTime(timezone=True))
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )
