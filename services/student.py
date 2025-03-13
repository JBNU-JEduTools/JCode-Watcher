import numpy as np
from sqlmodel import Session
from crud.student import get_snapshot_data, get_assignment_snapshots, get_build_log, get_run_log
from datetime import datetime, timedelta
from fastapi import HTTPException
import pytz
from collections import defaultdict
from schemas.student import BuildLogResponse, RunLogResponse

def format_timestamp(timestamp: str) -> str:
    return datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")

def calculate_snapshot_avg(db: Session, class_div: str, hw_name: str, student_id: int, filename: str):
    results = get_snapshot_data(db, class_div, hw_name, student_id, filename)
    
    if not results:
        return None
    
    snapshot_avg = len(results)
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0

    return {
        "snapshot_avg": snapshot_avg,
        "snapshot_size_avg": snapshot_size_avg
    }


def calculate_assignment_snapshot_avg(db: Session, class_div: str, student_id: int, hw_name: str):
    results = get_assignment_snapshots(db, class_div, student_id, hw_name)
    
    if not results:
        return None
    
    timestamps = sorted(
        snapshot.timestamp for snapshot in results
    )
    
    first_timestamp = timestamps[0]
    last_timestamp = timestamps[-1]
    first = datetime.strptime(first_timestamp, "%Y%m%d_%H%M%S")
    last = datetime.strptime(last_timestamp, "%Y%m%d_%H%M%S")
    total = (last - first).total_seconds()
    interval = 0

    if len(timestamps) > 1:
        second_last_timestamp = timestamps[-2]
        second_last = datetime.strptime(second_last_timestamp, "%Y%m%d_%H%M%S")
        interval = (last - second_last).total_seconds()
    else:
        interval = 0
    
    snapshot_counts = len(results)
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0

    return {
        "snapshot_avg": snapshot_counts,
        "snapshot_size_avg": snapshot_size_avg,
        "first": first, 
        "last": last,
        "total": total,           #초 단위
        "interval": interval
    }

def adjust_to_interval(base_minute: int, current_minute: int, interval: int) -> int:
    """
    base_minute을 기준으로 current_minute이 속하는 interval 구간의 시작 시간을 반환
    """
    diff = current_minute - base_minute
    group = diff // interval
    return base_minute + (group * interval)

def graph_data_by_minutes(db: Session, class_div: str, hw_name: str, student_id: int, interval: int):
    """
    전체 데이터를 기준으로 지정된 interval(분 단위)로 평균 코드량과 변화량을 집계.
    """
    if interval <= 0:
        raise HTTPException(status_code=400, detail="Interval must be a positive integer.")

    # 데이터 가져오기
    results = get_assignment_snapshots(db, class_div, student_id, hw_name)
    if not results:
        return {"trends": []}

    kst = pytz.timezone("Asia/Seoul")

    # 가장 오래된 데이터의 timestamp 찾기
    min_time = None
    for snapshot in results:
        snapshot_time = datetime.strptime(snapshot.timestamp, "%Y%m%d_%H%M%S")
        snapshot_time = kst.localize(snapshot_time)
        
        if min_time is None or snapshot_time < min_time:
            min_time = snapshot_time

    if min_time is None:
        return {"trends": []}  # 데이터가 없으면 빈 리스트 반환

    # 시작 시간을 기준으로 설정 (반올림하지 않음)
    base_minute = min_time.minute
    
    # 데이터를 interval 단위로 그룹화
    size_by_minute = defaultdict(int)
    count_by_minute = defaultdict(int)

    for snapshot in results:
        snapshot_time = datetime.strptime(snapshot.timestamp, "%Y%m%d_%H%M%S")
        snapshot_time = kst.localize(snapshot_time)
        
        # 현재 시간의 분을 시작 시간 기준으로 interval 구간 시작점으로 조정
        adjusted_minute = adjust_to_interval(base_minute, snapshot_time.minute, interval)
        
        # 시간 조정이 필요한 경우
        extra_hours = adjusted_minute // 60
        final_minutes = adjusted_minute % 60
        
        adjusted_time = snapshot_time.replace(
            hour=(snapshot_time.hour + extra_hours) % 24,
            minute=final_minutes,
            second=0,
            microsecond=0
        )
        
        minute_key = adjusted_time.strftime("%Y%m%d_%H%M")
        size_by_minute[minute_key] += snapshot.file_size
        count_by_minute[minute_key] += 1

    # 코드 변화량 및 평균 코드량 계산
    sorted_minutes = sorted(size_by_minute.keys())  # timestamp 오름차순 정렬
    trends = []
    
    prev_size = 0
    for timestamp in sorted_minutes:
        total_size = size_by_minute[timestamp]
        count = count_by_minute[timestamp]

        avg_size = round(total_size / count, 2) if count > 0 else 0.00
        size_change = round(avg_size - prev_size, 2)

        trends.append({"timestamp": timestamp, "total_size": avg_size, "size_change": size_change})
        prev_size = avg_size

    return {"trends": trends}

def fetch_build_log(db: Session, class_div: str, hw_name: str, student_id: int) -> list[BuildLogResponse]:
    results = get_build_log(db, class_div, hw_name, student_id)
    return [BuildLogResponse(
        exit_code=result.exit_code,
        cmdline=result.cmdline,
        cwd=result.cwd,
        binary_path=result.binary_path,
        timestamp=result.timestamp
    ) for result in results]

def fetch_run_log(db: Session, class_div: str, hw_name: str, student_id: int) -> list[RunLogResponse]:
    results = get_run_log(db, class_div, hw_name, student_id)
    return [RunLogResponse(
        cmdline=result.cmdline,
        exit_code=result.exit_code,
        cwd=result.cwd,
        target_path=result.target_path,
        process_type=result.process_type,
        timestamp=result.timestamp
    ) for result in results]