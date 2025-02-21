from sqlmodel import Session
from pathlib import Path
from app.models.snapshot import Snapshot

def snapshot_register(db: Session, snapshot_data):
    snapshot = Snapshot(
        class_div=snapshot_data["class_div"],
        hw_name=snapshot_data["hw_name"],
        student_id=snapshot_data["student_id"],
        filename=snapshot_data["filename"],
        timestamp=snapshot_data["timestamp"],
        file_size=snapshot_data["file_size"]
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    return snapshot
    
    