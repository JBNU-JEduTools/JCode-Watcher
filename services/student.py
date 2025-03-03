import numpy as np
from sqlmodel import Session
from crud.student import get_snapshot_data, get_assignment_snapshots
from datetime import datetime

def format_timestamp(timestamp: str) -> str:
    return datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")

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
    
    timestamps = sorted(
        snapshot.timestamp for snapshot in results
    )
    
    first_timestamp = timestamps[0]
    last_timestamp = timestamps[-1]
    first = datetime.strptime(first_timestamp, "%Y%m%d_%H%M%S")
    last = datetime.strptime(last_timestamp, "%Y%m%d_%H%M%S")
    total = (last - first).total_seconds()
    interval = 0

    if len(timestamps) > 1:
        second_last_timestamp = timestamps[-2]
        second_last = datetime.strptime(second_last_timestamp, "%Y%m%d_%H%M%S")
        interval = (last - second_last).total_seconds()
    else:
        interval = 0
    
    snapshot_counts = len(results)
    snapshot_size_avg = round(np.mean([snapshot.file_size for snapshot in results]), 2) if results else 0

    return {
        "snapshot_avg": snapshot_counts,
        "snapshot_size_avg": snapshot_size_avg,
        "first": first, 
        "last": last,
        "total": total,           #초 단위
        "interval": interval
    }
    
def fetch_graph_data(db: Session, class_div: str, hw_name: str, student_id: int):
    results = get_assignment_snapshots(db, class_div, student_id, hw_name)
    
    if not results:
        return None
    
    snapshot_trends = {}
    
    for snapshot in results:
        key = snapshot.filename
        if key not in snapshot_trends:
            snapshot_trends[key] = []
            
        snapshot_trends[key].append({
            "timestamp": format_timestamp(snapshot.timestamp),
            "size": snapshot.file_size
        })
        
    for key in snapshot_trends:
        snapshot_trends[key].sort(key=lambda x: x["timestamp"])
    
    return {"snapshot_trends" : snapshot_trends}
