from pydantic import BaseModel

class SnapshotAvgResponse(BaseModel):
    snapshot_avg: int
    snapshot_size_avg: float
