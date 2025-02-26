from sqlmodel import SQLModel
from typing import Dict, List

class AssignmentResponse(SQLModel):
    percentile_90: float
    percentile_50: float
    top: List[Dict[str, str | int | float]]
    avg_bytes: float
    avg_num: float