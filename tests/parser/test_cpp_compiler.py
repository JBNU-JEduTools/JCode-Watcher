import pytest
from pathlib import Path
from src.parser.cpp_compiler import CPPCompilerParser
from src.process.types import ProcessType

@pytest.fixture
def gpp_parser():
    return CPPCompilerParser(ProcessType.GPP)

@pytest.fixture
def test_dir(tmp_path):
    # 테스트 디렉토리 구조 생성
    source_files = [
        'main.cpp',
        'helper.cc',
        'utils.cxx',
        'complex_name-1.2.cpp',
        'old_code.c',
        'test.h',
        'config.hpp'
    ]
    
    # 메인 디렉토리
    for file_name in source_files:
        (tmp_path / file_name).touch()
    
    # include 서브디렉토리
    include_dir = tmp_path / 'include'
    include_dir.mkdir()
    (include_dir / 'header1.hpp').touch()
    
    # src 서브디렉토리
    src_dir = tmp_path / 'src'
    src_dir.mkdir()
    (src_dir / 'module.cpp').touch()
    
    return tmp_path

class TestCPPCompilerParser:
    def test_basic_compilation(self, gpp_parser, test_dir):
        """기본 컴파일 명령어 테스트"""
        args = "main.cpp -o main"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'
        
    def test_multiple_source_files(self, gpp_parser, test_dir):
        """여러 소스 파일 컴파일 테스트"""
        args = "main.cpp helper.cc utils.cxx -o program"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 3
        assert all(Path(f).name in ['main.cpp', 'helper.cc', 'utils.cxx'] for f in result.source_files)

    def test_c_source_file(self, gpp_parser, test_dir):
        """C 소스 파일 컴파일 테스트 (g++은 .c 파일도 C++로 컴파일)"""
        args = "old_code.c -o program"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'old_code.c'

    def test_complex_include_paths(self, gpp_parser, test_dir):
        """복잡한 include 경로 테스트"""
        args = ("-I/usr/include -I./include -I../common/include "
                "-I/opt/local/include main.cpp -o main")
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'

    def test_cpp_specific_defines(self, gpp_parser, test_dir):
        """C++ 관련 매크로 정의 테스트"""
        args = ("-D_GLIBCXX_DEBUG -DCPP_VERSION=\\\"17\\\" "
                "-DUSE_STL=1 -DTEMPLATE_MAX_ARGS=10 main.cpp -o main")
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'

    def test_optimization_flags(self, gpp_parser, test_dir):
        """최적화 플래그 테스트"""
        args = "-O3 -march=native -mtune=native -ffast-math main.cpp -o main"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'

    def test_cpp_standard_flags(self, gpp_parser, test_dir):
        """C++ 표준 플래그 테스트"""
        args = "-std=c++17 -fpermissive main.cpp -o main"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'

    def test_source_files_with_path(self, gpp_parser, test_dir):
        """경로가 포함된 소스 파일 테스트"""
        args = "./src/module.cpp main.cpp -o program"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 2
        assert any('module.cpp' in f for f in result.source_files)
        assert any('main.cpp' in f for f in result.source_files)

    def test_complex_file_names(self, gpp_parser, test_dir):
        """복잡한 파일 이름 테스트"""
        args = "complex_name-1.2.cpp -o complex"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'complex_name-1.2.cpp'

    def test_include_files_option(self, gpp_parser, test_dir):
        """include 파일 옵션 테스트"""
        args = "-include config.hpp -include test.h main.cpp -o main"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'

    def test_mixed_options(self, gpp_parser, test_dir):
        """혼합된 옵션 테스트"""
        args = ("-Wall -O2 -g -pipe -fPIC -shared "
                "-DNDEBUG -D_GNU_SOURCE "
                "-I./include -I/usr/local/include "
                "main.cpp helper.cc -o libtest.so")
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 2
        assert all(Path(f).name in ['main.cpp', 'helper.cc'] for f in result.source_files)

    def test_cpp_specific_options(self, gpp_parser, test_dir):
        """C++ 특정 옵션 테스트"""
        args = ("-fno-rtti -fno-exceptions -fno-threadsafe-statics "
                "-ftemplate-depth=1024 main.cpp -o main")
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 1
        assert Path(result.source_files[0]).name == 'main.cpp'

    def test_mixed_cpp_extensions(self, gpp_parser, test_dir):
        """다양한 C++ 확장자 테스트"""
        args = "main.cpp helper.cc utils.cxx -o program"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 3
        assert all(Path(f).name in ['main.cpp', 'helper.cc', 'utils.cxx'] for f in result.source_files)

    def test_no_source_files_with_complex_options(self, gpp_parser, test_dir):
        """소스 파일 없이 복잡한 옵션만 있는 경우 테스트"""
        args = ("-Wall -O2 -DDEBUG -I./include -L/usr/lib "
                "-fPIC -shared -o libtest.so")
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 0

    def test_relative_path_resolution(self, gpp_parser, test_dir):
        """상대 경로 해석 테스트"""
        args = "../project/main.cpp ./src/module.cpp -o program"
        result = gpp_parser.parse(args, str(test_dir))
        
        assert len(result.source_files) == 2
        assert all(Path(f).is_absolute() for f in result.source_files) 