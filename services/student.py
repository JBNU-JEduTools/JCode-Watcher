import numpy as np
from sqlmodel import Session
from app.crud.student import get_snapshot_data, get_assignment_snapshots


def calculate_snapshot_avg(db: Session, class_div: str, hw_name: str, student_id: int, filename: str):
    results = get_snapshot_data(db, class_div, hw_name, student_id, filename)
    
    if not results:
        return None
    
    snapshot_avg = len(results)
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0

    return {
        "snapshot_avg": snapshot_avg,
        "snapshot_size_avg": snapshot_size_avg
    }


def calculate_assignment_snapshot_avg(db: Session, class_div: str, student_id: int, hw_name: str):
    results = get_assignment_snapshots(db, class_div, student_id, hw_name)
    
    if not results:
        return None
    
    snapshot_counts = len(results)
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0

    return {
        "snapshot_avg": snapshot_counts,
        "snapshot_size_avg": snapshot_size_avg
    }

def get_graph_data(db: Session, class_div: str, hw_name: str, student_id: int):
    results = get_assignment_snapshots(db, class_div, student_id, hw_name)
    
    if not results:
        return None
    
    snapshot_trends = {}
    
    for snapshot in results:
        key = snapshot.filename
        if key not in snapshot_trends:
            snapshot_trends[key] = []
            
        snapshot_trends[key].append({
            "timestamp": snapshot.timestamp,
            "size": snapshot.file_size
        })
        
    for key in snapshot_trends:
        snapshot_trends[key].sort(key=lambda x: x["timestamp"])
    
    return {"snapshot_trends" : snapshot_trends}
