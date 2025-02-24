from collections import defaultdict
import numpy as np
from app.schemas.assignment import AssignmentResponse
from app.crud.assignment import get_monitoring_data
from sqlmodel import Session

def calculate_monitoring_data(db: Session, class_div: str, hw_name: str):
    results = get_monitoring_data(db, class_div, hw_name)
    
    if not results:
        return None
    
    latest_code_sizes = {}
    latest_timestamps = {}
    student_code_sizes = defaultdict(list)
    assignment_code_sizes = defaultdict(list)
    all_code_sizes = []
    
    for snapshot in results:
        student_id = snapshot.student_id
        filename = snapshot.filename
        file_size = snapshot.file_size
        timestamp = snapshot.timestamp
        
        all_code_sizes.append(file_size)
        assignment_code_sizes[hw_name].append(file_size)
        student_code_sizes[student_id].append(file_size)
        
        if filename not in latest_code_sizes or timestamp > latest_timestamps[filename]:
            latest_code_sizes[filename] = file_size
            latest_timestamps[filename] = timestamp
            
    percentile_90 = float(np.percentile(all_code_sizes, 90)) if all_code_sizes else 0
    percentile_50 = float(np.percentile(all_code_sizes, 50)) if all_code_sizes else 0
    
    return {
        "percentile_90": percentile_90,
        "percentile_50": percentile_50,
        "latest_code_sizes": latest_code_sizes,
        "latest_timestamps": latest_timestamps,
        "student_code_sizes": student_code_sizes,
        "assignment_code_sizes": assignment_code_sizes
    }
