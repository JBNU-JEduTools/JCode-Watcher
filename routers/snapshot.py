from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from pathlib import Path
from db.connection import get_session
from sqlmodel import Session
from fastapi import Depends
from crud.snapshot import snapshot_register
from schemas.snapshot import SnapshotCreate
from schemas.config import settings
from urllib.parse import unquote

router = APIRouter(tags=["Snapshot"])

BASE_DIR = Path(settings.BASE_DIR)

@router.post("/api/{class_div}/{hw_name}/{student_id}/{filename}/{timestamp}")
def register_snapshot(
    class_div: str,
    hw_name: str,
    student_id: str,
    filename: str,
    timestamp: str,
    file_size: SnapshotCreate = Body(...),
    db: Session=Depends(get_session)
):
    
    # file_depth = unquote(filename).replace('@', '/')   # 모든 @ 문자를 / 로 변환
    
    snapshot_data = {
        "class_div": class_div,
        "hw_name": hw_name,
        "student_id": student_id,
        "filename": filename,
        "timestamp": timestamp,
        "file_size": file_size.bytes
    }
    snapshot = snapshot_register(db=db, snapshot_data=snapshot_data)
    return {"message": "Snapshot registered successfully", "snapshot": snapshot}

# 스냅샷 파일 내용 조회
# nginx 설정 필요
@router.get("/static/{class_div}/{hw_name}/{student_id}/snapshots/{filename}/{timestamp}")
def get_static_file(
    class_div: str,
    hw_name: str,
    student_id: str,
    filename: str,
    timestamp: str,
):
    file_path = BASE_DIR / class_div / hw_name / student_id / filename / timestamp
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return FileResponse(path=file_path)

