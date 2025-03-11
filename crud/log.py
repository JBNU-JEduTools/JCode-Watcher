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
        exit_code=build_data["exit_code"],
        command_line=build_data["command_line"],
        pod_name=build_data["pod_name"],
        container_id=build_data["container_id"],
        pid=build_data["pid"],
        source_file=build_data["source_file"],
        compiler_path=build_data["compiler_path"],
        working_dir=build_data["working_dir"],
        error_flags=build_data["error_flags"]
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
        exit_code=run_data["exit_code"],
        command_line=run_data["command_line"],
        pod_name=run_data["pod_name"],
        container_id=run_data["container_id"],
        pid=run_data["pid"],
        binary_path=run_data["binary_path"],
        working_dir=run_data["working_dir"],
        error_flags=run_data["error_flags"]
    )
    
    db.add(run_log)
    db.commit()
    db.refresh(run_log)
    
    return run_log
    
    