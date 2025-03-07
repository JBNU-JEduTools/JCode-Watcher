import numpy as np
from sqlmodel import Session
from crud.student import get_snapshot_data, get_assignment_snapshots
from datetime import datetime, timedelta
from fastapi import HTTPException
import pytz
from collections import defaultdict

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
    
def fetch_graph_data(db: Session, class_div: str, hw_name: str, student_id: int):
    results = get_assignment_snapshots(db, class_div, student_id, hw_name)
    
    if not results:
        return None
    
    snapshot_trends = {}
    
    for snapshot in results:
        key = snapshot.filename
        if key not in snapshot_trends:
            snapshot_trends[key] = []
            
        snapshot_trends[key].append({
            "timestamp": format_timestamp(snapshot.timestamp),
            "size": snapshot.file_size
        })
        
    for key in snapshot_trends:
        snapshot_trends[key].sort(key=lambda x: x["timestamp"])
    
    return {"snapshot_trends" : snapshot_trends}

def round_to_interval(dt: datetime, interval: int) -> datetime:
    """
    주어진 datetime 객체를 interval(분) 단위로 반올림.
    """
    minute = (dt.minute // interval) * interval
    if dt.minute % interval >= interval / 2:
        minute += interval  # 반올림 적용
    return dt.replace(minute=minute, second=0, microsecond=0)

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

    # 시작 시간을 interval 단위로 반올림
    base_time = round_to_interval(min_time, interval)

    # 데이터를 interval 단위로 그룹화 (평균 계산을 위해 합산과 개수를 따로 저장)
    size_by_minute = defaultdict(int)  # { "YYYYMMDD_HHMM": total_size }
    count_by_minute = defaultdict(int) # 각 interval에 포함된 데이터 개수

    for snapshot in results:
        snapshot_time = datetime.strptime(snapshot.timestamp, "%Y%m%d_%H%M%S")
        snapshot_time = kst.localize(snapshot_time)

        # interval 단위로 반올림하여 key 생성
        adjusted_time = round_to_interval(snapshot_time, interval)
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

