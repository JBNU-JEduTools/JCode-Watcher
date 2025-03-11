from pydantic import BaseModel
from datetime import datetime

class BuildLogCreate(BaseModel):
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

class RunLogCreate(BaseModel):
    pod_name: str
    container_id: str
    pid: int
    binary_path: str
    working_dir: str
    command_line: str
    exit_code: int
    error_flags: str
    timestamp: datetime