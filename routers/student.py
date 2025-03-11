from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from collections import defaultdict
import numpy as np
from schemas.student import SnapshotAvgResponse, GraphResponse, MonitoringResponse, BuildLogResponse, RunLogResponse
from db.connection import get_session
from services.student import calculate_snapshot_avg, calculate_assignment_snapshot_avg, graph_data_by_minutes, fetch_build_log, fetch_run_log
from sqlmodel import Session
from typing import List

# 학생별
router = APIRouter(tags=["Student"])

# 학생별, 코드별 평균 스냅샷 개수, 크기 계산
@router.get("/api/snapshot_avg/{class_div}/{hw_name}/{student_id}/{filename}", response_model=SnapshotAvgResponse)
def get_snapshot_avg(
    class_div: str, 
    hw_name: str, 
    student_id: int, 
    filename: str, 
    db: Session = Depends(get_session)
):
    
    results = calculate_snapshot_avg(db, class_div, hw_name, student_id, filename)
    
    if not results:
        return SnapshotAvgResponse(snapshot_avg=None, snapshot_size_avg=None)

    return results
    

# 학생별, 과제별 평균 스냅샷 개수, 크기 계산
@router.get("/api/assignments/snapshot_avg/{class_div}/{hw_name}/{student_id}", response_model=MonitoringResponse)
def get_assignment_snapshot_avg(class_div: str, student_id: int, hw_name: str, db: Session = Depends(get_session)):
    result = calculate_assignment_snapshot_avg(db, class_div, student_id, hw_name)
    
    if not result:
        return MonitoringResponse(
            snapshot_avg=None,
            snapshot_size_avg=None,
            first=None,
            last=None,
            total=None,
            interval=None
        )
    
    return result
    
    
# 학생별 그래프 데이터 조회 - 시간별 스냅샷 크기 변화
@router.get("/api/graph_data/{class_div}/{hw_name}/{student_id}/{interval}", response_model=GraphResponse)
def get_graph_data_by_minutes(class_div: str, hw_name: str, student_id: int, interval: int, db: Session = Depends(get_session)):
    result = graph_data_by_minutes(db, class_div, hw_name, student_id, interval)
    
    if not result:
        return {"trends": []}
    
    return result

# 빌드 로그 조회
@router.get("/api/{class_div}/{hw_name}/{student_id}/logs/build", response_model=List[BuildLogResponse])
def get_build_log(class_div: str, hw_name: str, student_id: int, db: Session = Depends(get_session)):
    result = fetch_build_log(db, class_div, hw_name, student_id)

    return result if result else []

# 실행 로그 조회
@router.get("/api/{class_div}/{hw_name}/{student_id}/logs/run", response_model=List[RunLogResponse])
def get_run_log(class_div: str, hw_name: str, student_id: int, db: Session = Depends(get_session)):
    result = fetch_run_log(db, class_div, hw_name, student_id)

    return result if result else []