from pydantic import Field
from schemas.event import EventIdentityCreate


class SnapshotCreate(EventIdentityCreate):
    relative_path: str = Field(min_length=1, max_length=1024)
    file_size: int = Field(ge=0)
