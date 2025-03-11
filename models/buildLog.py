from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime

class BuildLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    class_div: str
    hw_name: str
    student_id: int
    pod_name: str
    container_id: str
    pid: int
    source_file: str
    compiler_path: str
    working_dir: str
    command_line: str
    exit_code: int
    error_flags: str
    timestamp: datetime