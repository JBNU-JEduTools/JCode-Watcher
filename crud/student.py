from sqlmodel import Session, select
from models.snapshot import Snapshot
from fastapi import HTTPException
import numpy as np
from models.buildLog import BuildLog
from models.runLog import RunLog

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
