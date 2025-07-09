import pytest
from pathlib import Path
from src.parser.python import PythonParser
from src.process.types import ProcessType

@pytest.fixture
def parser():
    return PythonParser(process_type=ProcessType.PYTHON)

def test_basic_python_script(parser):
    """기본 파이썬 스크립트 실행 테스트"""
    result = parser.parse("script.py", "/home/student/hw1")
    assert result.process_type == ProcessType.PYTHON
    assert result.source_files == ["/home/student/hw1/script.py"]
    assert result.cwd == "/home/student/hw1"

def test_script_with_arguments(parser):
    """스크립트 인자가 있는 경우 테스트"""
    # 일반적인 인자
    result = parser.parse("script.py arg1 arg2", "/home/student/hw1")
    assert result.source_files == ["/home/student/hw1/script.py"]
    
    # 옵션 형태의 인자
    result = parser.parse("script.py --verbose -o output.txt", "/home/student/hw1")
    assert result.source_files == ["/home/student/hw1/script.py"] 
    
    # 복잡한 인자들
    result = parser.parse(
        "pacman.py -p ApproximateQAgent -x 2000 -n 2010 -l smallGrid",
        "/home/student/hw1"
    )
    assert result.source_files == ["/home/student/hw1/pacman.py"]

def test_multiple_py_files(parser):
    """여러 .py 파일이 인자로 주어진 경우 테스트"""
    # 첫 번째 .py 파일만 소스로 인식해야 함
    result = parser.parse("main.py test.py data.py", "/home/student/hw1")
    assert result.source_files == ["/home/student/hw1/main.py"]
    
    # .py 파일이 나중에 나오는 경우
    result = parser.parse("--config test.py other.py", "/home/student/hw1")
    assert result.source_files == ["/home/student/hw1/test.py"]

def test_unsupported_options(parser):
    """지원하지 않는 옵션 테스트"""
    # -m 옵션
    result = parser.parse("-m pytest", "/home/student/hw1")
    assert result.source_files == []
    
    # -c 옵션
    result = parser.parse('-c "print(1)"', "/home/student/hw1")
    assert result.source_files == []

def test_no_py_file(parser):
    """파이썬 스크립트가 없는 경우 테스트"""
    # 일반 인자만 있는 경우
    result = parser.parse("arg1 arg2 --verbose", "/home/student/hw1")
    assert result.source_files == []
    
    # 빈 인자
    result = parser.parse("", "/home/student/hw1")
    assert result.source_files == []

def test_m_option_cases(parser):
    """다양한 -m 옵션 케이스 테스트"""
    # 기본적인 -m 옵션
    result = parser.parse("-m pytest", "/home/student/hw1")
    assert result.source_files == []
    
    # -m 옵션과 함께 .py 파일이 있는 경우
    result = parser.parse("-m pytest test_file.py", "/home/student/hw1")
    assert result.source_files == []
    
    # -m 옵션이 중간에 있는 경우
    result = parser.parse("--verbose -m pytest test_file.py", "/home/student/hw1")
    assert result.source_files == []
    
    # -m 옵션이 여러 인자와 함께 있는 경우
    result = parser.parse("-m pytest test_file.py --verbose -v", "/home/student/hw1")
    assert result.source_files == [] 