from fastapi import APIRouter, HTTPException, Body, Request
from fastapi.responses import FileResponse, Response
from pathlib import Path
from db.connection import get_session
from sqlmodel import Session
from fastapi import Depends
from datetime import datetime
import pytz
from crud.log import build_register, run_register
from schemas.log import BuildLogCreate, RunLogCreate

router = APIRouter(tags=["Log"])
kst = pytz.timezone('Asia/Seoul')

#빌드 로그 등록
@router.post("/api/{class_div}/{hw_name}/{student_id}/logs/build")
def register_build_log(
    class_div: str,
    hw_name: str,
    student_id: int,
    log_data: BuildLogCreate = Body(...),
    db: Session=Depends(get_session)
):
    timestamp_kst = log_data.timestamp.astimezone(kst)

    build_data = {
        "class_div": class_div,
        "hw_name": hw_name,
        "student_id": student_id,
        "timestamp": timestamp_kst,
        "cwd": log_data.cwd,
        "binary_path": log_data.binary_path,
        "cmdline": log_data.cmdline,
        "exit_code": log_data.exit_code,
        "target_path": log_data.target_path
    }
    
    build_log = build_register(db=db, build_data=build_data)
    return {"message": "Build log registered successfully", "build_log": build_log}
    
#실행 로그 등록
@router.post("/api/{class_div}/{hw_name}/{student_id}/logs/run")
def register_run_log(
    class_div: str,
    hw_name: str,
    student_id: int,
    log_data: RunLogCreate = Body(...), 
    db: Session=Depends(get_session)
):

    timestamp_kst = log_data.timestamp.astimezone(kst)

    run_data = {
        "class_div": class_div,
        "hw_name": hw_name,
        "student_id": student_id,
        "timestamp": timestamp_kst,
        "cmdline": log_data.cmdline,
        "exit_code": log_data.exit_code,
        "cwd": log_data.cwd,
        "target_path": log_data.target_path,
        "process_type": log_data.process_type
    }
    
    run_log = run_register(db=db, run_data=run_data)
    return {"message": "Run log registered successfully", "run_log": run_log}