import numpy as np
from sqlmodel import Session
from crud.student import get_snapshot_data, get_assignment_snapshots, get_build_log, get_run_log, get_closest_snapshot
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
    # 스냅샷 평균 크기 - 전체 스냅샷 파일 사이즈 총합 / 스냅샷 총 개수
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0

    return {
        "snapshot_avg": snapshot_counts,    # 스냅샷 총 개수
        "snapshot_size_avg": snapshot_size_avg, # 스냅샷 평균 크기
        "first": first,  # 첫 스냅샷 시간
        "last": last,    # 마지막 스냅샷 시간
        "total": total,           # 총 작업 시간 (초 단위)
        "interval": interval    # 마지막 스냅샷과 두 번째 스냅샷의 시간 차이 (초 단위)
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
    total_size_by_minute = {}
    latest_sizes_by_filename = {}  # {filename: latest_file_size} 저장용

    sorted_snapshots = sorted(results, key=lambda s: s.timestamp)

    for snapshot in sorted_snapshots:
        snapshot_time = datetime.strptime(snapshot.timestamp, "%Y%m%d_%H%M%S")
        snapshot_time = kst.localize(snapshot_time)
        
        # min_time으로부터 경과한 분
        elapsed_minutes = int((snapshot_time - min_time).total_seconds() // 60)

        # interval 단위로 구간 조정
        bucketed_minutes = (elapsed_minutes // interval) * interval

        # 조정된 시간 계산 (일자 포함)
        adjusted_time = min_time + timedelta(minutes=bucketed_minutes)
        
        minute_key = adjusted_time.strftime("%Y%m%d_%H%M")
        
        #현재 파일의 최신 file_size
        latest_sizes_by_filename[snapshot.filename] = snapshot.file_size

        # 현재까지의 최신 파일별 file_size 합산
        total_code_size = sum(latest_sizes_by_filename.values())
        total_size_by_minute[minute_key] = total_code_size

    # 코드 변화량 및 평균 코드량 계산
    sorted_minutes = sorted(total_size_by_minute.keys())  # timestamp 오름차순 정렬
    trends = []
    
    prev_size = 0
    for timestamp in sorted_minutes:
        total_size = total_size_by_minute[timestamp]
        size_change = round(total_size - prev_size, 2)

        trends.append({"timestamp": timestamp, "total_size": total_size, "size_change": size_change})
        prev_size = total_size

    return {"trends": trends}

def fetch_build_log(db: Session, class_div: str, hw_name: str, student_id: int) -> list[BuildLogResponse]:
    results = get_build_log(db, class_div, hw_name, student_id)

    responses = []
    for result in results:
        file_size = get_closest_snapshot(db, class_div, hw_name, student_id, result.timestamp)
        responses.append(BuildLogResponse(
            exit_code=result.exit_code,
            cmdline=result.cmdline,
            cwd=result.cwd,
            binary_path=result.binary_path,
            target_path=result.target_path,
            timestamp=result.timestamp,
            file_size=file_size))
        
    return responses

def fetch_run_log(db: Session, class_div: str, hw_name: str, student_id: int) -> list[RunLogResponse]:
    results = get_run_log(db, class_div, hw_name, student_id)
    
    responses = []
    for result in results:
        file_size = get_closest_snapshot(db, class_div, hw_name, student_id, result.timestamp)
        responses.append(RunLogResponse(
            cmdline=result.cmdline,
            exit_code=result.exit_code,
            cwd=result.cwd,
            target_path=result.target_path,
            process_type=result.process_type,
            timestamp=result.timestamp,
            file_size=file_size))
        
    return responses
