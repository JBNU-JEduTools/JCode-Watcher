"""파일 비교 유틸리티"""
from pathlib import Path

class FileComparator:
    """파일 비교 클래스"""
    
    @staticmethod
    def is_different(file1: Path, file2: Path, chunk_size: int = 8192) -> bool:
        """두 파일의 내용 비교"""
        if file1.stat().st_size != file2.stat().st_size:
            return True
            
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                chunk1 = f1.read(chunk_size)
                chunk2 = f2.read(chunk_size)
                if chunk1 != chunk2:
                    return True
                if not chunk1:  # EOF
                    return False 