from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import numpy as np
from app.db.connection import get_session
from app.crud.assignment import get_monitoring_data
from app.services.assignment import calculate_monitoring_data
from sqlmodel import Session
from app.schemas.assignment import AssignmentResponse

# 전체 학생 대상(한 과제 안에서)
router = APIRouter(tags=["Assignment"])

# 전체 학생 대상 퍼센타일 계산
@router.get("/api/assignment/{class_div}/{hw_name}", response_model=AssignmentResponse)
def get_assignment_data(class_div: str, hw_name: str, db: Session = Depends(get_session)):
    result = calculate_monitoring_data(db, class_div, hw_name)
    
    if not result:
        raise HTTPException(status_code=404, detail="No monitoring data found")
    
    return result
