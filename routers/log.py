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
        "exit_code": log_data.exit_code, 
        "command_line": log_data.command_line,
        "pod_name": log_data.pod_name,
        "container_id": log_data.container_id,
        "pid": log_data.pid,
        "source_file": log_data.source_file,
        "compiler_path": log_data.compiler_path,
        "working_dir": log_data.working_dir,
        "error_flags": log_data.error_flags
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
        "exit_code": log_data.exit_code,
        "command_line": log_data.command_line,
        "pod_name": log_data.pod_name,
        "container_id": log_data.container_id,
        "pid": log_data.pid,
        "binary_path": log_data.binary_path,
        "working_dir": log_data.working_dir,
        "error_flags": log_data.error_flags
    }
    
    run_log = run_register(db=db, run_data=run_data)
    return {"message": "Run log registered successfully", "run_log": run_log}