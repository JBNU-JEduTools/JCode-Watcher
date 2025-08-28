import pytest
from app.models.process_type import ProcessType
from app.file_parser import FileParser


class TestFileParser:
    """FileParser 테스트"""
    
    def setup_method(self):
        """Given: FileParser 인스턴스 생성"""
        self.parser = FileParser()
    
    # Python 파일 파싱 테스트
    def test_python_file_parsing(self):
        """Python 파일 파싱 테스트"""
        # Given: 다양한 Python 명령어 인자 패턴
        test_cases = [
            (["script.py"], "script.py"),
            (["script.py", "arg1", "arg2"], "script.py"),
            (["main.py", "--verbose"], "main.py"),
            (["/path/to/script.py"], "/path/to/script.py"),
            (["arg1", "script.py", "arg2"], "script.py"),
        ]
        
        for args, expected in test_cases:
            # When: Python 타입으로 인자를 파싱할 때
            result = self.parser.parse(ProcessType.PYTHON, args)
            
            # Then: 첫 번째 .py 파일이 반환되어야 함
            assert result == expected, f"Failed to parse '{args}', expected '{expected}', got '{result}'"
    
    def test_python_module_execution(self):
        """Python 모듈 실행 시 파일 없음"""
        # Given: -m 옵션을 사용한 모듈 실행 명령어
        module_args = [
            ["-m", "pytest"],
            ["python", "-m", "http.server"],
            ["-m", "json.tool"],
        ]
        
        for args in module_args:
            # When: 모듈 실행 명령을 파싱할 때
            result = self.parser.parse(ProcessType.PYTHON, args)
            
            # Then: 파일을 찾지 못해야 함 (None 반환)
            assert result is None, f"Should not find file in module execution: '{args}'"
    
    def test_python_with_options(self):
        """Python 옵션이 있는 경우"""
        test_cases = [
            (["-u", "script.py"], "script.py"),
            (["--verbose", "script.py", "arg1"], "script.py"),
            (["-O", "-u", "script.py"], "script.py"),
        ]
        
        for args, expected in test_cases:
            result = self.parser.parse(ProcessType.PYTHON, args)
            assert result == expected, f"Failed to parse '{args}', expected '{expected}', got '{result}'"
    
    # C/C++ 파일 파싱 테스트
    def test_c_file_parsing(self):
        """C 파일 파싱 테스트"""
        # Given: 다양한 C 컴파일 명령어 패턴
        test_cases = [
            (["main.c"], "main.c"),
            (["main.c", "-o", "program"], "main.c"),
            (["-Wall", "main.c", "-o", "test"], "main.c"),
            (["src/main.c"], "src/main.c"),
            (["/absolute/path/main.c", "-g"], "/absolute/path/main.c"),
        ]
        
        for args, expected in test_cases:
            for process_type in [ProcessType.GCC, ProcessType.CLANG]:
                # When: GCC 또는 CLANG 타입으로 인자를 파싱할 때
                result = self.parser.parse(process_type, args)
                
                # Then: 첫 번째 .c 파일이 반환되어야 함
                assert result == expected, f"Failed to parse '{args}' for {process_type}, expected '{expected}', got '{result}'"
    
    def test_cpp_file_parsing(self):
        """C++ 파일 파싱 테스트"""
        cpp_files = ["main.cpp", "test.cc", "program.cxx", "app.c++", "CLASS.C"]
        
        for cpp_file in cpp_files:
            args = [cpp_file, "-o", "program"]
            result = self.parser.parse(ProcessType.GPP, args)
            assert result == cpp_file, f"Failed to parse C++ file: '{cpp_file}'"
    
    def test_compiler_skip_options(self):
        """컴파일러 옵션 건너뛰기 테스트"""
        test_cases = [
            (["-o", "output", "main.c"], "main.c"),
            (["-I/usr/include", "main.c"], "main.c"),  
            (["-include", "header.h", "main.c"], "main.c"),
            (["-D", "DEBUG", "main.c"], "main.c"),
            (["-U", "NDEBUG", "main.c"], "main.c"),
            (["-MF", "deps.d", "main.c"], "main.c"),
        ]
        
        for args, expected in test_cases:
            result = self.parser.parse(ProcessType.GCC, args)
            assert result == expected, f"Failed to skip options in '{args}', expected '{expected}', got '{result}'"
    
    def test_multiple_source_files_returns_first(self):
        """여러 소스 파일 중 첫 번째 반환"""
        args = ["first.c", "second.c", "third.c"]
        result = self.parser.parse(ProcessType.GCC, args)
        assert result == "first.c", f"Should return first source file, got '{result}'"
    
    def test_no_source_files(self):
        """소스 파일이 없는 경우"""
        no_source_args = [
            ["-Wall", "-O2", "-g"],
            ["--help"],
            ["-v"],
            [],  # 빈 리스트
        ]
        
        for args in no_source_args:
            result = self.parser.parse(ProcessType.GCC, args)
            assert result is None, f"Should return None for '{args}', got '{result}'"
    
    def test_unsupported_process_type(self):
        """지원하지 않는 프로세스 타입"""
        # Given: 지원하지 않는 프로세스 타입
        unsupported_types = [ProcessType.UNKNOWN, ProcessType.USER_BINARY]
        args = ["main.c"]
        
        for process_type in unsupported_types:
            # When: 지원하지 않는 타입으로 파싱할 때
            result = self.parser.parse(process_type, args)
            
            # Then: None이 반환되어야 함
            assert result is None
    
    def test_empty_or_none_args(self):
        """빈 리스트나 None 인자"""
        for args in [None, []]:
            result = self.parser.parse(ProcessType.GCC, args)
            assert result is None, f"Should return None for empty args: '{args}'"
    
    def test_complex_gcc_command(self):
        """복잡한 GCC 명령어"""
        args = ["gcc", "-Wall", "-Wextra", "-std=c99", "-O2", "-I/usr/include", "-L/usr/lib", "-o", "myprogram", "main.c", "-lm"]
        result = self.parser.parse(ProcessType.GCC, args)
        assert result == "main.c", f"Should find main.c in complex command, got '{result}'"
    
    def test_files_with_spaces(self):
        """공백이 포함된 파일명 테스트 - 이제 올바르게 처리됨"""
        test_cases = [
            # Python files with spaces
            (ProcessType.PYTHON, ["my script.py"], "my script.py"),
            (ProcessType.PYTHON, ["my script.py", "arg1", "arg2"], "my script.py"),
            (ProcessType.PYTHON, ["-u", "final project.py"], "final project.py"),
            
            # C/C++ files with spaces  
            (ProcessType.GCC, ["my project.c"], "my project.c"),
            (ProcessType.GCC, ["my project.c", "-o", "output"], "my project.c"),
            (ProcessType.GCC, ["-Wall", "final project.c", "-o", "program"], "final project.c"),
            (ProcessType.GPP, ["my program.cpp"], "my program.cpp"),
            
            # Files with multiple spaces and special characters
            (ProcessType.GCC, ["project with   spaces.c"], "project with   spaces.c"),
            (ProcessType.PYTHON, ["script-with-dashes and spaces.py"], "script-with-dashes and spaces.py"),
        ]
        
        for process_type, args, expected in test_cases:
            result = self.parser.parse(process_type, args)
            assert result == expected, f"Failed to parse file with spaces: process_type={process_type}, args={args}, expected='{expected}', got='{result}'"


if __name__ == "__main__":
    pytest.main([__file__])