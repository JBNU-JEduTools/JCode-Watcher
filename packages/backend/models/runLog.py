from models.common import EventIdentity
from sqlalchemy import Column, Index, Integer, String, Text, desc
from sqlmodel import Field


class RunLog(EventIdentity, table=True):
    __tablename__ = "run_event"
    __table_args__ = (
        Index(
            "ix_run_assignment_student_time",
            "assignment_id",
            "student_key",
            desc("occurred_at"),
            desc("id"),
        ),
        Index(
            "ix_run_assignment_time", "assignment_id", desc("occurred_at"), desc("id")
        ),
    )
    cmdline: str = Field(sa_column=Column(Text, nullable=False))
    exit_code: int = Field(sa_column=Column(Integer, nullable=False))
    cwd: str = Field(sa_column=Column(Text, nullable=False))
    target_path: str = Field(sa_column=Column(Text, nullable=False))
    process_type: str = Field(sa_column=Column(String(32), nullable=False))
