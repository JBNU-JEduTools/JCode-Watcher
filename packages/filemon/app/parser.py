from pathlib import Path
from app.models.source_file_info import SourceFileInfo
from app.config.settings import settings

class SourceFileParser:
    """
    소스 파일 경로를 파싱하고 스냅샷 경로를 생성하는 클래스
    """
    def parse(self, source_path: str | Path) -> SourceFileInfo:
        """
        소스 파일 경로로부터 SourceFileInfo 객체 생성
        
        Args:
            source_path: 소스 파일 경로
            
        Returns:
            SourceFileInfo: 경로 정보 객체
            
        Raises:
            ValueError: 경로 형식이 잘못된 경우
        """
        source = Path(source_path)
        try:
            relative_path = source.relative_to(settings.BASE_PATH)
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
            
            return SourceFileInfo(
                class_div=class_div,
                hw_name=hw_name,
                student_id=student_id,
                filename=filename,
                source_path=source
            )
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"잘못된 경로 형식: {source_path}") from e

    def get_snapshot_dir(self, path_info: SourceFileInfo) -> Path:
        """스냅샷 디렉토리 경로 생성"""
        return (settings.SNAPSHOT_BASE / 
                path_info.class_div / 
                path_info.hw_name / 
                path_info.student_id /
                self._get_nested_path(path_info))

    def get_snapshot_path(self, path_info: SourceFileInfo, timestamp: str) -> Path:
        """
        스냅샷 파일 경로 생성
        
        Args:
            path_info: 경로 정보 객체
            timestamp: 타임스탬프 (예: 20240316_123456)
            
        Returns:
            Path: 스냅샷 파일 경로
        """
        return self.get_snapshot_dir(path_info) / f"{timestamp}{path_info.source_path.suffix}"

    def _get_nested_path(self, path_info: SourceFileInfo) -> str:
        """과제 디렉토리 이후의 경로를 @로 결합하여 반환"""
        path = Path(path_info.source_path)
        hw_index = -1
        for i, part in enumerate(path.parts):
            if part == path_info.hw_name:
                hw_index = i
                break
        
        if hw_index == -1:
            raise ValueError(f"과제 디렉토리를 찾을 수 없음: {path_info.source_path}")
        
        nested_parts = path.parts[hw_index + 1:]
        return '@'.join(nested_parts)