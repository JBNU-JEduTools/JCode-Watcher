import pytest
from pathlib import Path
from src.parser.compiler import CCompilerParser
from src.process.types import ProcessType

@pytest.fixture
def gcc_parser():
    return CCompilerParser(ProcessType.GCC)

@pytest.fixture
def clang_parser():
    return CCompilerParser(ProcessType.CLANG)

@pytest.fixture
def test_dir(tmp_path):
    # 테스트 디렉토리 구조 생성
    source_files = [
        'main.c',
        'helper.c',
        'utils.c',
        'complex_name-1.2.c',
        'test.h',
        'config.h'
    ]
    
    # 메인 디렉토리
    for file_name in source_files:
        (tmp_path / file_name).touch()
    
    # include 서브디렉토리
    include_dir = tmp_path / 'include'
    include_dir.mkdir()
    (include_dir / 'header1.h').touch()
    
    # src 서브디렉토리
    src_dir = tmp_path / 'src'
    src_dir.mkdir()
    (src_dir / 'module.c').touch()
    
    return tmp_path

class TestCCompilerParser:
    def test_basic_compilation(self, gcc_parser, test_dir):
        """기본 컴파일 명령어 테스트"""
        args = "main.c -o main"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'
        
    def test_multiple_source_files(self, gcc_parser, test_dir):
        """여러 소스 파일 컴파일 테스트"""
        args = "main.c helper.c utils.c -o program"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 3
        assert all(Path(f).name in ['main.c', 'helper.c', 'utils.c'] for f in result.source_files)

    def test_complex_include_paths(self, gcc_parser, test_dir):
        """복잡한 include 경로 테스트"""
        args = ("-I/usr/include -I./include -I../common/include "
                "-I/opt/local/include main.c -o main")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_multiple_defines(self, gcc_parser, test_dir):
        """여러 매크로 정의 테스트"""
        args = ("-DDEBUG -DVERSION=\\\"1.0\\\" -DMAX_BUFFER=1024 "
                "-DFEATURE_X main.c -o main")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_optimization_flags(self, gcc_parser, test_dir):
        """최적화 플래그 테스트"""
        args = "-O3 -march=native -mtune=native -ffast-math main.c -o main"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_warning_flags(self, gcc_parser, test_dir):
        """경고 플래그 테스트"""
        args = ("-Wall -Wextra -Werror -Wconversion -Wshadow "
                "-Wno-unused-parameter main.c -o main")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_source_files_with_path(self, gcc_parser, test_dir):
        """경로가 포함된 소스 파일 테스트"""
        args = "./src/module.c main.c -o program"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 2
        assert any('module.c' in f for f in result.source_files)
        assert any('main.c' in f for f in result.source_files)

    def test_complex_file_names(self, gcc_parser, test_dir):
        """복잡한 파일 이름 테스트"""
        args = "complex_name-1.2.c -o complex"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'complex_name-1.2.c'

    def test_include_files_option(self, gcc_parser, test_dir):
        """include 파일 옵션 테스트"""
        args = "-include config.h -include test.h main.c -o main"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_mixed_options(self, gcc_parser, test_dir):
        """혼합된 옵션 테스트"""
        args = ("-Wall -O2 -g -pipe -fPIC -shared "
                "-DNDEBUG -D_GNU_SOURCE "
                "-I./include -I/usr/local/include "
                "main.c helper.c -o libtest.so")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 2
        assert all(Path(f).name in ['main.c', 'helper.c'] for f in result.source_files)

    def test_gcc_specific_options(self, gcc_parser, test_dir):
        """GCC 특정 옵션 테스트"""
        args = ("-fprofile-generate -ftest-coverage -fprofile-arcs "
                "-fstack-protector-strong main.c -o main")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_clang_specific_options(self, clang_parser, test_dir):
        """Clang 특정 옵션 테스트"""
        args = ("-Weverything -fcolor-diagnostics -fno-sanitize=address "
                "main.c -o main")
        result = clang_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_dependency_generation(self, gcc_parser, test_dir):
        """의존성 생성 옵션 테스트"""
        args = ("-MD -MP -MF main.d -MT main.o "
                "main.c -o main")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.c'

    def test_no_source_files_with_complex_options(self, gcc_parser, test_dir):
        """소스 파일 없이 복잡한 옵션만 있는 경우 테스트"""
        args = ("-Wall -O2 -DDEBUG -I./include -L/usr/lib "
                "-fPIC -shared -o libtest.so")
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 0

    def test_relative_path_resolution(self, gcc_parser, test_dir):
        """상대 경로 해석 테스트"""
        args = "../project/main.c ./src/module.c -o program"
        result = gcc_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 2
        assert all(Path(f).is_absolute() for f in result.source_files) 