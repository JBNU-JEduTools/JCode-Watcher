from pydantic import Field
from schemas.event import EventIdentityCreate


class BuildLogCreate(EventIdentityCreate):
    binary_path: str = Field(max_length=4096)
    cmdline: str = Field(max_length=16384)
    exit_code: int
    cwd: str = Field(max_length=4096)
    target_path: str = Field(max_length=4096)


class RunLogCreate(EventIdentityCreate):
    cmdline: str = Field(max_length=16384)
    exit_code: int
    cwd: str = Field(max_length=4096)
    target_path: str = Field(max_length=4096)
    process_type: str = Field(min_length=1, max_length=32)
