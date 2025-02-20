from fastapi import APIRouter
from pathlib import Path
import numpy as np

BASE_DIR = Path("/home/ubuntu/Couch")

# 전체 학생 대상(한 과제 안에서)
router = APIRouter(tags=["Total"])

# 전체 학생 대상 퍼센타일 계산
@router.get("/api/percentile")
def get_percentile(hw_name: str):
    # path = BASE_DIR / hw_name
    latest_code_sizes = {}
    latest_timestamps = {}
    student_code_sizes = {}
    assignment_code_sizes = {}
    all_code_sizes = []
    
    for student_id in BASE_DIR.iterdir():
        if not student_id.is_dir():
            continue
        
        student_code_sizes[student_id] = []
        
        for assignment in student_id.iterdir():
            if not assignment.is_dir():
                continue
            
            assignment_code_sizes.setdefault(assignment.name, [])
            
            for code_name in assignment.iterdir():
                if not code_name.is_dir():
                    continue
                
                latest_snapshot = None
                latest_timestamp = None
                for snapshot in code_name.iterdir():
                    timestamp = int(snapshot.name)
                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp
                        latest_snapshot = snapshot
                    
                if latest_snapshot and latest_snapshot.is_file():
                    code_size = latest_snapshot.stat().st_size
                    all_code_sizes.append(code_size)
                    assignment_code_sizes[assignment.name].append(code_size)
                    student_code_sizes[student_id].append(code_size)
                    
                    latest_code_sizes[code_name.name] = code_size
                    latest_timestamps[code_name.name] = latest_timestamp
                    
    percentile_90 = np.percentile(all_code_sizes, 90)
    percentile_50 = np.percentile(all_code_sizes, 50)
    
    return {    
        "percentile_90": percentile_90,
        "percentile_50": percentile_50,
        "latest_code_sizes": latest_code_sizes,
        "latest_timestamps": latest_timestamps,
        "student_code_sizes": student_code_sizes,
        "assignment_code_sizes": assignment_code_sizes
    }

# # 전체 학생 대상 최근 스냅샷 계산
# @router.get("/api/last_snapshot")
# def get_total():
#     return {"message": "Hello World"}

# # 전체 학생 대상 과제 평균 계산
# @router.get("/api/hw_avg")
# def get_total():
#     return {"message": "Hello World"}

