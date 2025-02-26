from collections import defaultdict
import numpy as np
from app.crud.assignment import get_monitoring_data
from sqlmodel import Session

# 퍼센타일, 전체 학생별 평균 bytes&개수, 최근 작업자(타임스탬프, 학번, 사이즈) 
def calculate_monitoring_data(db: Session, class_div: str, hw_name: str):
    results = get_monitoring_data(db, class_div, hw_name)
    
    if not results:
        return None
    
    latest_student = {}
    student_code_sizes = defaultdict(list)      # 학생별 파일 크기 리스트
    snapshot_num = defaultdict(int)
    all_code_sizes = []
    
    for snapshot in results:
        student_id = snapshot.student_id
        filename = snapshot.filename
        file_size = snapshot.file_size
        timestamp = snapshot.timestamp
        
        all_code_sizes.append(file_size)
        student_code_sizes[student_id].append(file_size)
        snapshot_num[student_id] += 1
        
        # 최신 제출만 저장 (더 최신 타임스탬프가 있으면 업데이트)
        if student_id not in latest_student or timestamp > latest_student[student_id][0]:
            latest_student[student_id] = (timestamp, file_size)
        
    percentile_90 = round(float(np.percentile(all_code_sizes, 90)), 2) if all_code_sizes else 0
    percentile_50 = round(float(np.percentile(all_code_sizes, 50)), 2) if all_code_sizes else 0
    
    top_students = sorted(latest_student.items(), key=lambda x: x[1][0], reverse=True)[:7]
    top_7 = [
        {"student_id": student_id, "timestamp": data[0], "code_size": data[1]}
        for student_id, data in top_students
    ]
    
    # 각 학생별 평균 bytes 계산
    avg_bytes_per_student = {
        student_id: sum(sizes) / len(sizes)
        for student_id, sizes in student_code_sizes.items()
    }
    
    avg_bytes = round(sum(avg_bytes_per_student.values()) / len(avg_bytes_per_student), 2) if avg_bytes_per_student else 0

    # 전체 평균 스냅샷 개수 계산
    avg_snapshots_per_student = round(sum(snapshot_num.values()) / len(snapshot_num), 2) if snapshot_num else 0
    
    return {
        "percentile_90": percentile_90,                  # 90% 퍼센타일(상위 10% 경계값)
        "percentile_50": percentile_50,                  # 50% 퍼센타일(데이터 중앙값)
        "top": top_7,
        "avg_bytes": avg_bytes,
        "avg_num": avg_snapshots_per_student
    }
