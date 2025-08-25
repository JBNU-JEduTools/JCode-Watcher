import pytest
from src.models.process_type import ProcessType
from src.classifier import ProcessClassifier


class TestProcessClassifier:
    """ProcessClassifier 테스트"""
    
    def setup_method(self):
        """Given: ProcessClassifier 인스턴스 생성"""
        self.classifier = ProcessClassifier()
    
    def test_gcc_classification(self):
        """GCC 컴파일러 분류 테스트"""
        # Given: 다양한 버전의 GCC 경로들
        gcc_paths = [
            "/usr/bin/x86_64-linux-gnu-gcc-9",
            "/usr/bin/x86_64-linux-gnu-gcc-11",
            "/usr/bin/x86_64-linux-gnu-gcc-13",
        ]
        
        for path in gcc_paths:
            # When: 경로를 분류할 때
            result = self.classifier.classify(path)
            
            # Then: GCC로 분류되어야 함
            assert result == ProcessType.GCC, f"Failed to classify {path} as GCC"
    
    def test_clang_classification(self):
        """Clang 컴파일러 분류 테스트"""
        # Given: 다양한 버전의 Clang 경로들
        clang_paths = [
            "/usr/lib/llvm-14/bin/clang",
            "/usr/lib/llvm-15/bin/clang",
            "/usr/lib/llvm-18/bin/clang",
        ]
        
        for path in clang_paths:
            # When: 경로를 분류할 때
            result = self.classifier.classify(path)
            
            # Then: CLANG으로 분류되어야 함
            assert result == ProcessType.CLANG, f"Failed to classify {path} as CLANG"
    
    def test_gpp_classification(self):
        """G++ 컴파일러 분류 테스트"""
        # Given: 다양한 버전의 G++ 경로들
        gpp_paths = [
            "/usr/bin/x86_64-linux-gnu-g++-9",
            "/usr/bin/x86_64-linux-gnu-g++-11", 
            "/usr/bin/x86_64-linux-gnu-g++-13",
        ]
        
        for path in gpp_paths:
            # When: 경로를 분류할 때
            result = self.classifier.classify(path)
            
            # Then: GPP로 분류되어야 함
            assert result == ProcessType.GPP, f"Failed to classify {path} as GPP"
    
    def test_python_classification(self):
        """Python 인터프리터 분류 테스트"""
        # Given: 다양한 버전의 Python 경로들
        python_paths = [
            "/usr/bin/python3.8",
            "/usr/bin/python3.9",
            "/usr/bin/python3.10",
            "/usr/bin/python3.11",
        ]
        
        for path in python_paths:
            # When: 경로를 분류할 때
            result = self.classifier.classify(path)
            
            # Then: PYTHON으로 분류되어야 함
            assert result == ProcessType.PYTHON, f"Failed to classify {path} as PYTHON"
    
    def test_unknown_classification(self):
        """알 수 없는 바이너리 분류 테스트"""
        # Given: 알려지지 않은 바이너리 경로들
        unknown_paths = [
            "/usr/bin/ls",
            "/bin/sh", 
            "/usr/bin/vim",
            "/home/user/my_program",
            "/usr/bin/gcc",  # 버전 번호 없음
            "/usr/bin/python",  # 버전 번호 없음
        ]
        
        for path in unknown_paths:
            # When: 경로를 분류할 때
            result = self.classifier.classify(path)
            
            # Then: UNKNOWN으로 분류되어야 함
            assert result == ProcessType.UNKNOWN, f"Should classify {path} as UNKNOWN"
    
    def test_empty_path(self):
        """빈 경로 테스트"""
        # Given: 빈 문자열 경로
        empty_path = ""
        
        # When: 빈 경로를 분류할 때
        result = self.classifier.classify(empty_path)
        
        # Then: UNKNOWN으로 분류되어야 함
        assert result == ProcessType.UNKNOWN
    
    def test_none_path(self):
        """None 경로 테스트"""
        # Given: None 값
        none_path = None
        
        # When: None을 분류할 때
        result = self.classifier.classify(none_path)
        
        # Then: UNKNOWN으로 분류되어야 함
        assert result == ProcessType.UNKNOWN
    
    def test_partial_match_should_fail(self):
        """부분 매치는 실패해야 함 (fullmatch 사용)"""
        # Given: 부분적으로 매치되는 경로들
        partial_paths = [
            "usr/bin/x86_64-linux-gnu-gcc-11",  # 앞에 /가 없음
            "/usr/bin/x86_64-linux-gnu-gcc-11/extra",  # 뒤에 추가 경로
            "prefix/usr/bin/x86_64-linux-gnu-gcc-11",  # 앞에 prefix
        ]
        
        for path in partial_paths:
            # When: 부분 매치 경로를 분류할 때
            result = self.classifier.classify(path)
            
            # Then: UNKNOWN으로 분류되어야 함 (부분 매치 실패)
            assert result == ProcessType.UNKNOWN, f"Should not partially match {path}"


if __name__ == "__main__":
    pytest.main([__file__])