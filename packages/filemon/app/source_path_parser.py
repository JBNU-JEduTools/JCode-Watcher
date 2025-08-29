from pathlib import Path
from typing import Dict, Any


class SourcePathParser:
    """소스 파일 경로를 파싱하는 클래스"""
    
    def parse(self, target_file_path: Path, watch_root: Path) -> Dict[str, Any]:
        """소스 파일 경로를 파싱하여 구성 요소를 반환
        
        Args:
            target_file_path: 파싱할 대상 파일 경로
            watch_root: 감시 루트 경로
            
        Returns:
            Dict containing: class_div, hw_name, student_id, filename
            
        Raises:
            ValueError: 경로 구조가 올바르지 않을 때
        """
        # WATCH_ROOT 기준 상대 경로 계산
        try:
            relative_path = target_file_path.relative_to(watch_root)
        except ValueError:
            raise ValueError(f"파일 경로가 WATCH_ROOT 하위에 있지 않음: {target_file_path}")
        
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
        
        return {
            'class_div': class_div,
            'hw_name': hw_name,
            'student_id': student_id,
            'filename': filename
        }