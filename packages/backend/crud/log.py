from sqlmodel import Session
from pathlib import Path
from models.buildLog import BuildLog
from models.runLog import RunLog

def build_register(db: Session, build_data):
    build_log = BuildLog(
        class_div=build_data["class_div"],
        hw_name=build_data["hw_name"],
        student_id=build_data["student_id"],
        timestamp=build_data["timestamp"],
        cwd=build_data["cwd"],
        binary_path=build_data["binary_path"],
        cmdline=build_data["cmdline"],
        exit_code=build_data["exit_code"],
        target_path=build_data["target_path"]
    )
    
    db.add(build_log)
    db.commit()
    db.refresh(build_log)
    
    return build_log

def run_register(db: Session, run_data):
    run_log = RunLog(
        class_div=run_data["class_div"],
        hw_name=run_data["hw_name"],
        student_id=run_data["student_id"],
        timestamp=run_data["timestamp"],
        cmdline=run_data["cmdline"],
        exit_code=run_data["exit_code"],
        cwd=run_data["cwd"],
        target_path=run_data["target_path"],
        process_type=run_data["process_type"]
    )
    
    db.add(run_log)
    db.commit()
    db.refresh(run_log)
    
    return run_log
    
    