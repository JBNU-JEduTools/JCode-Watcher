from crud.selection import get_student_hw_files, get_student_hw_timestamps
from typing import List
from sqlmodel import Session

def fetch_student_hw_files(db: Session, class_div: str, student_id: int, hw_name: str) -> List[str]:
    snapshots = get_student_hw_files(db, class_div, student_id, hw_name)
    
    return snapshots

def fetch_student_hw_timestamps(db: Session, class_div: str, student_id: int, hw_name: str, filename: str) -> List[str]:
    return get_student_hw_timestamps(db, class_div, student_id, hw_name, filename)
