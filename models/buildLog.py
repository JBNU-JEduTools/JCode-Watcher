from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class BuildLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_div: str
    hw_name: str
    student_id: int
    cwd: str
    binary_path: str
    cmdline: str
    exit_code: int
    timestamp: datetime