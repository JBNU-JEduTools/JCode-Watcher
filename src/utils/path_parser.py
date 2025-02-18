"""경로 파싱 유틸리티"""
from pathlib import Path
from ..utils.logger import get_logger

class PathParser:
    """경로 파싱 클래스"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def _flatten_path(self, parts: list[str], hw_dir: str, filename: str) -> str:
        """hw_dir 이후의 경로를 플래트닝
        
        Args:
            parts: 전체 경로의 부분들
            hw_dir: 과제 디렉토리명 (예: hw1)
            filename: 원본 파일명
            
        Returns:
            str: 플래트닝된 파일명 (예: folder1@test.c)
        """
        try:
            # hw_dir 이후의 경로 찾기
            hw_index = parts.index(hw_dir)
            subpath_parts = parts[hw_index + 1:-1]  # hw_dir과 파일명 사이의 모든 디렉토리
            
            if not subpath_parts:  # 추가 디렉토리가 없는 경우
                self.logger.debug(f"하위 디렉토리 없음, 원본 파일명 사용: {filename}")
                return filename
                
            # 디렉토리들을 @로 연결하고 파일명 추가
            flattened = "@".join(subpath_parts + [filename])
            self.logger.debug(f"경로 플래트닝: {'/'.join(subpath_parts)}/{filename} -> {flattened}")
            return flattened
        except ValueError:
            self.logger.warning(f"과제 디렉토리를 찾을 수 없음, 원본 파일명 사용: {filename}")
            return filename
    
    def parse_path(self, file_path: str) -> tuple[str, str, str, str, str]:
        """파일 경로에서 필요한 정보 추출
        
        Args:
            file_path: 원본 파일 경로 (예: /watcher/codes/os-3-202012180/config/workspace/hw1/folder1/test.c)
            
        Returns:
            tuple[str, str, str, str, str]: (class_div, hw_dir, student_id, flattened_filename, original_path)
            예: ('os-3', 'hw1', '202012180', 'folder1@test.c', '/watcher/codes/.../test.c')
            -> snapshots/os-3/hw1/202012180/folder1@test.c/timestamp.c 형식으로 저장됨
        """
        path = Path(file_path)
        parts = list(path.parts)  # 리스트로 변환하여 인덱스 검색 가능하게 함
        
        try:
            # /watcher/codes/os-3-202012180/config/workspace/hw1/folder1/test.c 형식 가정
            if len(parts) < 4:
                raise ValueError(f"경로가 너무 짧습니다: {file_path}")
                
            # 학생 디렉토리명에서 정보 추출 (예: os-3-202012180)
            student_dir = parts[3]  # BASE_PATH 이후의 첫 번째 디렉토리
            class_info = student_dir.split('-')
            
            if len(class_info) != 3:
                raise ValueError(f"잘못된 클래스-분반-학번 형식: {student_dir}")
                
            course = class_info[0]
            division = class_info[1]
            student_id = class_info[2]  # 학번
            class_div = f"{course}-{division}"  # 예: os-3
            
            # 과제 디렉토리 찾기
            hw_dir = ""
            for part in parts:
                if part.startswith("hw"):
                    hw_dir = part
                    break
                    
            if not hw_dir:
                raise ValueError(f"과제 디렉토리를 찾을 수 없습니다: {file_path}")
                
            # 파일명 플래트닝
            flattened_filename = self._flatten_path(parts, hw_dir, path.name)
            
            self.logger.debug(f"경로 파싱 결과: class_div={class_div}, hw_dir={hw_dir}, student_id={student_id}, flattened_filename={flattened_filename}")
            return class_div, hw_dir, student_id, flattened_filename, file_path
            
        except Exception as e:
            self.logger.error(f"경로 파싱 실패: {file_path} - {str(e)}")
            raise ValueError(f"잘못된 파일 경로 형식: {file_path} - {str(e)}") 