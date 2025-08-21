import pytest
from src.models.process_type import ProcessType
from src.classifier import ProcessClassifier


class TestProcessClassifier:
    """ProcessClassifier 테스트"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.classifier = ProcessClassifier()
    
    def test_gcc_classification(self):
        """GCC 컴파일러 분류 테스트"""
        gcc_paths = [
            "/usr/bin/x86_64-linux-gnu-gcc-9",
            "/usr/bin/x86_64-linux-gnu-gcc-11",
            "/usr/bin/x86_64-linux-gnu-gcc-13",
        ]
        
        for path in gcc_paths:
            result = self.classifier.classify(path)
            assert result == ProcessType.GCC, f"Failed to classify {path} as GCC"
    
    def test_clang_classification(self):
        """Clang 컴파일러 분류 테스트"""
        clang_paths = [
            "/usr/lib/llvm-14/bin/clang",
            "/usr/lib/llvm-15/bin/clang",
            "/usr/lib/llvm-18/bin/clang",
        ]
        
        for path in clang_paths:
            result = self.classifier.classify(path)
            assert result == ProcessType.CLANG, f"Failed to classify {path} as CLANG"
    
    def test_gpp_classification(self):
        """G++ 컴파일러 분류 테스트"""
        gpp_paths = [
            "/usr/bin/x86_64-linux-gnu-g++-9",
            "/usr/bin/x86_64-linux-gnu-g++-11", 
            "/usr/bin/x86_64-linux-gnu-g++-13",
        ]
        
        for path in gpp_paths:
            result = self.classifier.classify(path)
            assert result == ProcessType.GPP, f"Failed to classify {path} as GPP"
    
    def test_python_classification(self):
        """Python 인터프리터 분류 테스트"""
        python_paths = [
            "/usr/bin/python3.8",
            "/usr/bin/python3.9",
            "/usr/bin/python3.10",
            "/usr/bin/python3.11",
        ]
        
        for path in python_paths:
            result = self.classifier.classify(path)
            assert result == ProcessType.PYTHON, f"Failed to classify {path} as PYTHON"
    
    def test_unknown_classification(self):
        """알 수 없는 바이너리 분류 테스트"""
        unknown_paths = [
            "/usr/bin/ls",
            "/bin/sh", 
            "/usr/bin/vim",
            "/home/user/my_program",
            "/usr/bin/gcc",  # 버전 번호 없음
            "/usr/bin/python",  # 버전 번호 없음
        ]
        
        for path in unknown_paths:
            result = self.classifier.classify(path)
            assert result == ProcessType.UNKNOWN, f"Should classify {path} as UNKNOWN"
    
    def test_empty_path(self):
        """빈 경로 테스트"""
        result = self.classifier.classify("")
        assert result == ProcessType.UNKNOWN
    
    def test_none_path(self):
        """None 경로 테스트"""
        result = self.classifier.classify(None)
        assert result == ProcessType.UNKNOWN
    
    def test_partial_match_should_fail(self):
        """부분 매치는 실패해야 함 (fullmatch 사용)"""
        partial_paths = [
            "usr/bin/x86_64-linux-gnu-gcc-11",  # 앞에 /가 없음
            "/usr/bin/x86_64-linux-gnu-gcc-11/extra",  # 뒤에 추가 경로
            "prefix/usr/bin/x86_64-linux-gnu-gcc-11",  # 앞에 prefix
        ]
        
        for path in partial_paths:
            result = self.classifier.classify(path)
            assert result == ProcessType.UNKNOWN, f"Should not partially match {path}"


if __name__ == "__main__":
    pytest.main([__file__])