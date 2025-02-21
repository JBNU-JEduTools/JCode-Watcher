from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.services.selection import fetch_student_hw_files, fetch_student_hw_timestamps
from typing import List
from app.db.connection import get_session

router = APIRouter(tags=["Selection"])

@router.get("/api/{class_div}/{hw_name}/{student_id}/", response_model=List[str])
def get_student_hw_files(class_div: str, student_id: int, hw_name: str, db: Session = Depends(get_session)):
    return fetch_student_hw_files(db, class_div, student_id, hw_name)

@router.get("/api/{class_div}/{hw_name}/{student_id}/{filename}/", response_model=List[str])
def get_student_hw_timestamps(class_div: str, student_id: int, hw_name: str, filename: str, db: Session = Depends(get_session)):
    return fetch_student_hw_timestamps(db, class_div, student_id, hw_name, filename)