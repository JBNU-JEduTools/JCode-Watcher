from collections import defaultdict
import numpy as np
from crud.assignment import get_monitoring_data, get_build_avg, get_run_avg
from sqlmodel import Session
from datetime import datetime
import pytz
from fastapi import FastAPI
from schemas.assignment import BuildAvgResponse, RunAvgResponse

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
        
        # 최신 스냅샷만 저장 (더 최신 타임스탬프가 있으면 업데이트)
        if student_id not in latest_student or timestamp > latest_student[student_id][0]:
            latest_student[student_id] = (timestamp, file_size)
        
    percentile_90 = round(float(np.percentile(all_code_sizes, 90)), 2) if all_code_sizes else 0
    percentile_50 = round(float(np.percentile(all_code_sizes, 50)), 2) if all_code_sizes else 0
    
    top_students = sorted(latest_student.items(), key=lambda x: x[1][0], reverse=True)[:7]
    top_7 = [
        {"student_num": student_id, "timestamp": data[0], "code_size": data[1]}
        for student_id, data in top_students
    ]
    
    # 각 학생별 평균 bytes 계산
    avg_bytes_per_student = {
        student_id: round(sum(sizes) / len(sizes), 2)
        for student_id, sizes in student_code_sizes.items()
    }
    avg_bytes = round(sum(avg_bytes_per_student.values()) / len(avg_bytes_per_student), 2) if avg_bytes_per_student else 0  # 학생별 평균 코드 크기값의 총합 / 학생 수

    # 전체 평균 스냅샷 개수 계산 (전체 스냅샷 개수 / 학생 수)
    avg_snapshots_per_student = round(sum(snapshot_num.values()) / len(snapshot_num), 2) if snapshot_num else 0
    
    return {
        "percentile_90": percentile_90,                  # 90% 퍼센타일(상위 10% 경계값)
        "percentile_50": percentile_50,                  # 50% 퍼센타일(데이터 중앙값)
        "top_7": top_7,
        "avg_bytes": avg_bytes,
        "avg_num": avg_snapshots_per_student
    }

def parse_timestamp(timestamp: str) -> datetime:
    try:
        if '_' in timestamp:  # YYYYMMDD_HHMMSS 형식
            return datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        else:  # ISO 형식
            return datetime.fromisoformat(timestamp.replace('Z', ''))
    except ValueError as e:
        print(f"Timestamp parsing error: {e} for timestamp: {timestamp}")
        raise

def fetch_total_graph_data(db: Session, class_div: str, hw_name: str, start: datetime, end: datetime):
    results = get_monitoring_data(db, class_div, hw_name)
    
    if not results:
        return None
    
    try:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
        
        filtered_results = []
        for snapshot in results:
            try:
                snapshot_time = parse_timestamp(snapshot.timestamp)
                if start <= snapshot_time <= end:
                    filtered_results.append(snapshot)
            except ValueError as e:
                print(f"Error processing snapshot: {e}")
                continue
        
        student_changes = {}

        for snapshot in filtered_results:
            timestamp_dt = parse_timestamp(snapshot.timestamp)

            if snapshot.student_id not in student_changes:
                student_changes[snapshot.student_id] = {"first": snapshot.file_size, "last": snapshot.file_size, "first_time": timestamp_dt}
            else:
                student_changes[snapshot.student_id]["last"] = snapshot.file_size
                student_changes[snapshot.student_id]["last_time"] = timestamp_dt

        result = [
            {
                "student_num": student_id,
                "size_change": abs(data["last"] - data["first"])
            }
            for student_id, data in student_changes.items()
        ]

        return {"results": result}
    except Exception as e:
        print(f"Error in fetch_graph_data: {e}")
        return {"results": []}
    
# 빌드 평균 횟수 계산
def calculate_build_avg(db: Session, class_div: str, hw_name: str) -> BuildAvgResponse:
    results = get_build_avg(db, class_div, hw_name)
    return BuildAvgResponse(avg_count=results)

# 실행 평균 횟수 계산
def calculate_run_avg(db: Session, class_div: str, hw_name: str) -> RunAvgResponse:
    results = get_run_avg(db, class_div, hw_name)
    return RunAvgResponse(avg_count=results)