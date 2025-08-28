import re
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SourceFileInfo:
    """소스 코드 경로 정보를 관리하는 클래스"""
    class_div: str      # 과목-분반 (예: os-1)
    hw_name: str        # 과제명 (예: hw1)
    student_id: str     # 학번 (예: 202012180)
    filename: str       # 파일명 (예: src@app@test.py)
    source_path: Path   # 원본 파일 전체 경로
    
    @classmethod
    def from_source_path(cls, source_path: Path, base_path: Path) -> 'SourceFileInfo':
        """소스 파일 경로로부터 SourceFileInfo 생성"""
        # BASE_PATH 기준 상대 경로 계산
        try:
            relative_path = source_path.relative_to(base_path)
        except ValueError:
            raise ValueError(f"파일 경로가 BASE_PATH 하위에 있지 않음: {source_path}")
        
        # 경로 파싱: class-div-student_id/hw_name/...
        parts = relative_path.parts
        if len(parts) < 3:
            raise ValueError(f"잘못된 경로 구조: {relative_path}")
        
        # 과목-분반과 학번 분리 (os-1-202012180 형식)
        class_student = parts[0].split('-')
        if len(class_student) != 3:
            raise ValueError(f"잘못된 디렉토리 형식: {parts[0]}")
            
        class_div = f"{class_student[0]}-{class_student[1]}"
        student_id = class_student[2]
        hw_name = parts[1]
        
        # 나머지 경로를 @로 결합하여 파일명 생성
        filename = '@'.join(parts[2:])
        
        return cls(
            class_div=class_div,
            hw_name=hw_name,
            student_id=student_id,
            filename=filename,
            source_path=source_path
        )
