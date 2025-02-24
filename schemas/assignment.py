from sqlmodel import SQLModel
from typing import Dict, List

class AssignmentResponse(SQLModel):
    percentile_90: float
    percentile_50: float
    latest_code_sizes: Dict[str, int]
    latest_timestamps: Dict[str, int]
    student_code_sizes: Dict[int, List[int]]
    assignment_code_sizes: Dict[str, List[int]]
