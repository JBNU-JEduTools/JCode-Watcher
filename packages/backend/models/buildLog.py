from models.common import EventIdentity
from sqlalchemy import Column, Index, Integer, Text, desc
from sqlmodel import Field


class BuildLog(EventIdentity, table=True):
    __tablename__ = "build_event"
    __table_args__ = (
        Index(
            "ix_build_assignment_student_time",
            "assignment_id",
            "student_key",
            desc("occurred_at"),
            desc("id"),
        ),
        Index(
            "ix_build_assignment_time", "assignment_id", desc("occurred_at"), desc("id")
        ),
    )
    cwd: str = Field(sa_column=Column(Text, nullable=False))
    binary_path: str = Field(sa_column=Column(Text, nullable=False))
    cmdline: str = Field(sa_column=Column(Text, nullable=False))
    exit_code: int = Field(sa_column=Column(Integer, nullable=False))
    target_path: str = Field(sa_column=Column(Text, nullable=False))
