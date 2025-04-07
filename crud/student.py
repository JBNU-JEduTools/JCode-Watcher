from sqlmodel import Session, select, func
from models.snapshot import Snapshot
from fastapi import HTTPException
import numpy as np
from models.buildLog import BuildLog
from models.runLog import RunLog
from datetime import datetime

def get_snapshot_data(db: Session, class_div:str, hw_name:str, student_id:int, filename:str):
    # 데이터베이스에서 해당 스냅샷 조회(select문)
    statement = select(Snapshot).where(
        Snapshot.class_div == class_div, 
        Snapshot.hw_name == hw_name, 
        Snapshot.student_id == student_id, 
        Snapshot.filename == filename
    )
    
    results = db.exec(statement).all()
    return results
    
def get_assignment_snapshots(db: Session, class_div: str, student_id: int, hw_name: str):
    statement = select(Snapshot).where(
        Snapshot.class_div == class_div,
        Snapshot.student_id == student_id,
        Snapshot.hw_name == hw_name
    )
    results = db.exec(statement).all()
    return results

def get_build_log(db: Session, class_div: str, hw_name: str, student_id: int):
    statement = select(BuildLog).where(
        BuildLog.class_div == class_div,
        BuildLog.hw_name == hw_name,
        BuildLog.student_id == student_id
    )
    results = db.exec(statement).all()
    return results

def get_run_log(db: Session, class_div: str, hw_name: str, student_id: int):
    statement = select(RunLog).where(
        RunLog.class_div == class_div,
        RunLog.hw_name == hw_name,
        RunLog.student_id == student_id
    )
    results = db.exec(statement).all()
    return results

def get_closest_snapshot(db: Session, class_div: str, hw_name: str, student_id: int, log_timestamp: datetime):
    log_timestamp_str = log_timestamp.strftime("%Y%m%d_%H%M%S")

    # 서브쿼리에서 파일별 최대 타임스탬프와 함께 모든 필요한 정보를 가져옴
    subquery = (
        select(
            Snapshot.filename,
            Snapshot.file_size,
            func.max(Snapshot.timestamp).label('max_timestamp')
        ).where(
            Snapshot.class_div == class_div,
            Snapshot.hw_name == hw_name,
            Snapshot.student_id == student_id,
            Snapshot.timestamp <= log_timestamp_str
        ).group_by(Snapshot.filename)
    )

    results = db.exec(subquery).all()

    # for result in results:
    #     print(f"파일: {result.filename}, 크기: {result.file_size}")
    
    total_code_size = sum(result.file_size for result in results) if results else 0
    # print(f"총 합계: {total_code_size}")
    # print("=================================")
    
    return total_code_size

def get_closest_snapshots_batch(db: Session, class_div: str, hw_name: str, student_id: int, log_timestamps: list[datetime]):
    # 모든 타임스탬프를 문자열로 변환
    log_timestamp_strs = [ts.strftime("%Y%m%d_%H%M%S") for ts in log_timestamps]
    
    # 결과를 저장할 딕셔너리
    file_sizes_by_timestamp = {}
    
    # 각 타임스탬프에 대해 한 번의 쿼리로 처리
    for timestamp_str in log_timestamp_strs:
        subquery = (
            select(
                Snapshot.filename,
                Snapshot.file_size,
                func.max(Snapshot.timestamp).label('max_timestamp')
            ).where(
                Snapshot.class_div == class_div,
                Snapshot.hw_name == hw_name,
                Snapshot.student_id == student_id,
                Snapshot.timestamp <= timestamp_str
            ).group_by(Snapshot.filename)
        )
        
        results = db.exec(subquery).all()
        total_code_size = sum(result.file_size for result in results) if results else 0
        file_sizes_by_timestamp[timestamp_str] = total_code_size
    
    # 원래 타임스탬프 순서대로 결과 반환
    return [file_sizes_by_timestamp[ts.strftime("%Y%m%d_%H%M%S")] for ts in log_timestamps]

