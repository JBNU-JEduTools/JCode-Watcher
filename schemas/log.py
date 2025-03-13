from pydantic import BaseModel
from datetime import datetime

class BuildLogCreate(BaseModel):
    binary_path: str
    cmdline: str
    exit_code: int
    cwd: str
    timestamp: datetime

class RunLogCreate(BaseModel):
    cmdline: str
    exit_code: int
    cwd: str
    target_path: str
    process_type: str
    timestamp: datetime