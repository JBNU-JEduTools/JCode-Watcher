from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import numpy as np
from db.connection import get_session
from crud.assignment import get_monitoring_data
from services.assignment import calculate_monitoring_data, fetch_total_graph_data, calculate_build_avg, calculate_run_avg
from sqlmodel import Session
from schemas.assignment import AssignmentResponse, CodeSizeChangeResponse, BuildAvgResponse, RunAvgResponse
from datetime import datetime

# 전체 학생 대상(한 과제 안에서)
router = APIRouter(tags=["Assignment"])

# 전체 학생 대상 퍼센타일 계산
@router.get("/api/assignment/{class_div}/{hw_name}", response_model=AssignmentResponse)
def get_assignment_data(class_div: str, hw_name: str, db: Session = Depends(get_session)):
    result = calculate_monitoring_data(db, class_div, hw_name)
    
    if not result:
        return AssignmentResponse(
            percentile_90=None,
            percentile_50=None,
            top_7=[],  # 빈 리스트 반환
            avg_bytes=None,
            avg_num=None
        )
    
    return result

@router.get("/api/total_graph_data/{class_div}/{hw_name}/{start}/{end}", response_model=CodeSizeChangeResponse)
async def get_graph_data(
    class_div: str, 
    hw_name: str, 
    start: datetime,  # str에서 datetime으로 변경
    end: datetime,    # str에서 datetime으로 변경
    db: Session = Depends(get_session)
):
    result = await fetch_total_graph_data(db, class_div, hw_name, start, end)

    if not result:
        return CodeSizeChangeResponse(results=[])
    
    return result

@router.get("/api/build_avg/{class_div}/{hw_name}", response_model=BuildAvgResponse)
def get_build_avg(class_div: str, hw_name: str, db: Session = Depends(get_session)):
    result = calculate_build_avg(db, class_div, hw_name)
    return result

@router.get("/api/run_avg/{class_div}/{hw_name}", response_model=RunAvgResponse)
def get_run_avg(class_div: str, hw_name: str, db: Session = Depends(get_session)):
    result = calculate_run_avg(db, class_div, hw_name)
    return result
