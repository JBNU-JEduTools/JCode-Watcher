from app.schemas.snapshot import Snapshot
from sqlmodel import Session
from pathlib import Path
from fastapi import HTTPException
BASE_DIR = Path("/home/ubuntu/watcher.v2/snapshots")

def snapshot_register(db: Session, snapshot: Snapshot):
    snapshot_dir = BASE_DIR / snapshot.class_div / snapshot.hw_name / snapshot.student_id / snapshot.filename
    
    if not snapshot_dir.exists():
        raise HTTPException(status_code=404, detail="Snapshot directory not found")
    