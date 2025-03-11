from fastapi import APIRouter, HTTPException, Body, Request
from fastapi.responses import FileResponse, Response
from pathlib import Path
from db.connection import get_session
from sqlmodel import Session
from fastapi import Depends
from crud.snapshot import snapshot_register
from schemas.snapshot import SnapshotCreate
from schemas.config import settings
from urllib.parse import unquote
from datetime import datetime, timezone, timedelta

router = APIRouter(tags=["Snapshot"])

def convert_to_kst(timestamp_str: str) -> datetime:
    dt_utc = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    return dt_utc + timedelta(hours=9)

#스냅샷 등록
@router.post("/api/{class_div}/{hw_name}/{student_id}/{filename}/{timestamp}")
def register_snapshot(
    class_div: str,
    hw_name: str,
    student_id: int,
    filename: str,
    timestamp: str,
    file_size: SnapshotCreate = Body(...),
    db: Session=Depends(get_session)
):
    
    timestamp_kst = convert_to_kst(timestamp)
    timestamp_kst_str = timestamp_kst.strftime("%Y%m%d_%H%M%S")
    
    # file_depth = unquote(filename).replace('@', '/')   # 모든 @ 문자를 / 로 변환
    
    snapshot_data = {
        "class_div": class_div,
        "hw_name": hw_name,
        "student_id": student_id,
        "filename": filename,
        "timestamp": timestamp_kst_str,
        "file_size": file_size.bytes
    }
    snapshot = snapshot_register(db=db, snapshot_data=snapshot_data)
    return {"message": "Snapshot registered successfully", "snapshot": snapshot}