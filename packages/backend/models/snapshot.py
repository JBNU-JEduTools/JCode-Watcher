from models.common import EventIdentity
from sqlalchemy import BigInteger, CheckConstraint, Column, Index, String, desc
from sqlmodel import Field


class Snapshot(EventIdentity, table=True):
    __tablename__ = "snapshot_event"
    __table_args__ = (
        CheckConstraint(
            "file_size >= 0", name="ck_snapshot_event_file_size_nonnegative"
        ),
        Index(
            "ix_snapshot_assignment_student_file_time",
            "assignment_id",
            "student_key",
            "relative_path",
            desc("occurred_at"),
            desc("id"),
        ),
        Index(
            "ix_snapshot_assignment_student_time",
            "assignment_id",
            "student_key",
            desc("occurred_at"),
            desc("id"),
        ),
        Index(
            "ix_snapshot_assignment_time",
            "assignment_id",
            desc("occurred_at"),
            desc("id"),
        ),
    )
    relative_path: str = Field(sa_column=Column(String(1024), nullable=False))
    file_size: int = Field(sa_column=Column(BigInteger, nullable=False))
