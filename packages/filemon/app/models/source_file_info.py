from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

@dataclass(frozen=True)
class SourceFileInfo:
    """소스 코드 경로 정보를 관리하는 클래스"""
    class_div: str      # 과목-분반 (예: os-1)
    hw_name: str        # 과제명 (예: hw1)
    student_id: str     # 학번 (예: 202012180)
    filename: str       # 파일명 (예: src@app@test.py)
    target_file_path: Path   # 대상 파일 절대 경로
    
    @classmethod
    def from_parsed_data(cls, parsed_data: Dict[str, Any], target_file_path: Path) -> 'SourceFileInfo':
        """파싱된 데이터로부터 SourceFileInfo 생성"""
        return cls(
            class_div=parsed_data['class_div'],
            hw_name=parsed_data['hw_name'],
            student_id=parsed_data['student_id'],
            filename=parsed_data['filename'],
            target_file_path=target_file_path
        )
