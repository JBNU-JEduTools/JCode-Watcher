from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from collections import defaultdict
import numpy as np
from app.schemas.student import SnapshotAvgResponse, GraphResponse
from app.crud.student import get_snapshot_data
from app.db.connection import get_session
from app.services.student import calculate_snapshot_avg, calculate_assignment_snapshot_avg, get_graph_data
from sqlmodel import Session
# BASE_DIR = Path("/home/ubuntu/watcher.v2/snapshots")

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
    
    results = get_snapshot_data(db, class_div, hw_name, student_id, filename)
    
    if not results:
        raise HTTPException(status_code=404, detail="Snapshot data not found")

    return results
    

# 학생별, 과제별 평균 스냅샷 개수, 크기 계산
@router.get("/api/assignments/snapshot_avg/{class_div}/{hw_name}/{student_id}", response_model=SnapshotAvgResponse)
def get_assignment_snapshot_avg(class_div: str, student_id: int, hw_name: str, db: Session = Depends(get_session)):
    result = calculate_assignment_snapshot_avg(db, class_div, student_id, hw_name)
    
    if not result:
        raise HTTPException(status_code=404, detail="Snapshot data not found")
    
    return result
    
    
# 학생별 그래프 데이터 조회 - 시간별 스냅샷 크기 변화
@router.get("/api/graph_data/{class_div}/{hw_name}/{student_id}", response_model=GraphResponse)
def get_graph_data(class_div: str, hw_name: str, student_id: str, db: Session = Depends(get_session)):
    result = get_graph_data(db, class_div, hw_name, student_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="No snapshot data found")
    
    return result

