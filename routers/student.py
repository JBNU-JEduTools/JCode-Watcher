from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from collections import defaultdict
import numpy as np
from app.schemas.student import SnapshotAvgResponse
from app.crud.student import get_snapshot_data
from app.db import get_db
from sqlmodel import Session
BASE_DIR = Path("/home/ubuntu/watcher.v2/snapshots")

# 학생별
router = APIRouter(tags=["Student"])

# 학생별, 코드별 평균 스냅샷 개수, 크기 계산
@router.get("/api/{class_div}/{hw_name}/{student_id}/{filename}/snapshot_avg", response_model=SnapshotAvgResponse)
def get_snapshot_avg(
    class_div: str, 
    hw_name: str, 
    student_id: int, 
    filename: str, 
    db: Session = Depends(get_db)
):
    
    results = get_snapshot_data(db, class_div, hw_name, student_id, filename)
    
    if not results:
        raise HTTPException(status_code=404, detail="Snapshot data not found")

    snapshot_avg = len(results)
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0
    
    return {
        "snapshot_avg": snapshot_avg,
        "snapshot_size_avg": snapshot_size_avg
    }
    

# =============================================== 아래는 리팩토링 필요

# 학생별, 과제별 평균 스냅샷 개수, 크기 계산
@router.get("/api/assignments/snapshot_avg")
def get_assignment_snapshot_avg(student_id: int, hw_name: str):
    # path = BASE_DIR / class_div / hw_name / student_id
    path = BASE_DIR / student_id / hw_name
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    
    snapshot_counts=[]
    snapshot_sizes=[]
    
    for code_file in path.iterdir():
        if code_file.is_dir():
            for snapshot in code_file.iterdir():
                if snapshot.is_file() and snapshot.name.isdigit():
                    snapshot_counts.append(1)
                    snapshot_sizes.append(snapshot.stat().st_size)
                    
    if not snapshot_counts:
        raise HTTPException(status_code=404, detail="No snapshot data found")
    
    snapshot_avg = len(snapshot_counts)  # 스냅샷 개수 평균
    snapshot_size_avg = round(np.mean(snapshot_sizes), 2) if snapshot_sizes else 0  # 스냅샷 크기 평균
    
    return {
        "snapshot_avg": snapshot_avg,
        "snapshot_size_avg": snapshot_size_avg
    }
    
# 학생별 그래프 데이터 조회 - 시간별 스냅샷 크기 변화
@router.get("/api/graph_data")
def get_graph_data(hw_name: str, student_id: str):
    # path = BASE_DIR / class_div / hw_name / student_id
    path = BASE_DIR / hw_name / student_id
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    
    snapshot_trends=defaultdict(list)
    for code_file in path.iterdir():
        if code_file.is_dir():
            for snapshot in code_file.iterdir():
                if snapshot.is_file() and snapshot.name.isdigit():
                    snapshot_trends[code_file.name].append({
                        "timestamp": snapshot.name,
                        "size": snapshot.stat().st_size
                    })
                    
            snapshot_trends[code_file.name].sort(key=lambda x: x["timestamp"])
    
    return {"snapshot_trends": snapshot_trends}

