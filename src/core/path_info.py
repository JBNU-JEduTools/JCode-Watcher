from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from src.utils.logger import get_logger

# 모듈 레벨 로거 설정
logger = get_logger(__name__)

@dataclass
class PathInfo:
    """소스 코드 경로 정보를 관리하는 클래스"""
    class_div: str      # 과목-분반 (예: os-1)
    hw_name: str        # 과제명 (예: hw1)
    student_id: str     # 학번 (예: 202012180)
    filename: str       # 파일명 (예: src@app@test.py)
    source_path: Path   # 원본 파일 전체 경로
    
    @classmethod
    def from_source_path(cls, source_path: str | Path, base_path: str | Path = '/watcher/codes') -> 'PathInfo':
        """
        소스 파일 경로로부터 PathInfo 객체 생성
        
        Args:
            source_path: 소스 파일 경로
            base_path: 기준 경로 (기본값: /watcher/codes)
            
        Returns:
            PathInfo: 경로 정보 객체
            
        Raises:
            ValueError: 경로 형식이 잘못된 경우
        """
        source = Path(source_path)
        try:
            relative_path = source.relative_to(base_path)
            path_parts = relative_path.parts
            
            # 과목-분반과 학번 분리 (os-1-202012180 형식)
            class_student = path_parts[0].split('-')
            if len(class_student) != 3:
                raise ValueError(f"잘못된 디렉토리 형식: {path_parts[0]}")
                
            class_div = f"{class_student[0]}-{class_student[1]}"
            student_id = class_student[2]
            hw_name = path_parts[1]
            
            # 나머지 경로를 @로 결합하여 파일명 생성
            filename = '@'.join(path_parts[2:])
            
            return cls(
                class_div=class_div,
                hw_name=hw_name,
                student_id=student_id,
                filename=filename,
                source_path=source
            )
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"잘못된 경로 형식: {source_path}") from e
            
    def get_snapshot_dir(self, snapshot_base: str | Path) -> Path:
        """스냅샷 디렉토리 경로 생성"""
        return (Path(snapshot_base) / 
                self.class_div / 
                self.hw_name / 
                self.student_id /
                self.source_path.name)

    def get_snapshot_path(self, snapshot_base: str | Path, timestamp: str) -> Path:
        """스냅샷 파일 경로 생성"""
        return self.get_snapshot_dir(snapshot_base) / f"{timestamp}{self.source_path.suffix}"