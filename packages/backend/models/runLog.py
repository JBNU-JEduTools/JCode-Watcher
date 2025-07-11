from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class RunLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_div: str
    hw_name: str
    student_id: int
    cmdline: str
    exit_code: int
    cwd: str
    target_path: str
    process_type: str
    timestamp: datetime