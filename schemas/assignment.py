from typing import List, Dict, Union, Optional
from sqlmodel import SQLModel

class AssignmentResponse(SQLModel):
    percentile_90: Optional[float] = None
    percentile_50: Optional[float] = None
    top_7: List[Dict[str, Union[str, int, float]]] = []
    avg_bytes: Optional[float] = None
    avg_num: Optional[float] = None
