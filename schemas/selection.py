from pydantic import BaseModel
from typing import List

class Selection_codefile(BaseModel):
    code_filename: str
    
    class Config:
        orm_mode = True

class Selection_snapshot(BaseModel):
    timestamps: List[str]