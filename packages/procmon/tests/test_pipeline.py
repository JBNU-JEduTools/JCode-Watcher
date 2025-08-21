import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import os
import ctypes

from src.pipeline import Pipeline
from src.models.process_struct import ProcessStruct, UTS_LEN, MAX_PATH_LEN, ARGSIZE
from src.models.process import Process
from src.models.process_type import ProcessType
from src.models.event import Event
from src.models.student_info import StudentInfo
from src.classifier import ProcessClassifier
from src.path_parser import PathParser
from src.file_parser import FileParser
from src.student_parser import StudentParser


class TestPipeline:
    """Pipeline 클래스 테스트"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.mock_classifier = Mock(spec=ProcessClassifier)
        self.mock_path_parser = Mock(spec=PathParser)
        self.mock_file_parser = Mock(spec=FileParser)
        self.mock_student_parser = Mock(spec=StudentParser)
        
        self.pipeline = Pipeline(
            classifier=self.mock_classifier,
            path_parser=self.mock_path_parser,
            file_parser=self.mock_file_parser,
            student_parser=self.mock_student_parser
        )
    
    def create_mock_process_struct(
        self,
        pid=1234,
        error_flags=0,
        hostname="jcode-os-1-202012180",
        binary_path="/usr/bin/x86_64-linux-gnu-gcc-11",
        cwd="/home/student/hw1",
        args=["gcc", "-o", "main", "main.c"],
        exit_code=0
    ):
        """ProcessStruct 모의 객체 생성"""
        struct = Mock(spec=ProcessStruct)
        struct.pid = pid
        struct.error_flags = error_flags
        
        # hostname 처리 - c_char 배열에 직접 decode 메서드를 추가
        hostname_bytes = hostname.encode('utf-8')
        hostname_array = (ctypes.c_char * UTS_LEN)(*hostname_bytes)
        hostname_array.decode = Mock(return_value=hostname)
        struct.hostname = hostname_array
        
        # binary_path 처리
        binary_bytes = binary_path.encode('utf-8') + b'\x00'
        binary_array = (ctypes.c_ubyte * MAX_PATH_LEN)()
        for i, b in enumerate(binary_bytes):
            if i < MAX_PATH_LEN:
                binary_array[i] = b
        struct.binary_path = binary_array
        struct.binary_path_offset = 0
        
        # cwd 처리
        cwd_bytes = cwd.encode('utf-8') + b'\x00'
        cwd_array = (ctypes.c_ubyte * MAX_PATH_LEN)()
        for i, b in enumerate(cwd_bytes):
            if i < MAX_PATH_LEN:
                cwd_array[i] = b
        struct.cwd = cwd_array
        struct.cwd_offset = 0
        
        # args 처리
        args_str = '\x00'.join(args) + '\x00'
        args_bytes = args_str.encode('utf-8')
        args_array = (ctypes.c_ubyte * ARGSIZE)()
        for i, b in enumerate(args_bytes):
            if i < ARGSIZE:
                args_array[i] = b
        struct.args = args_array
        struct.args_len = len(args_bytes)
        
        struct.exit_code = exit_code
        
        return struct


class TestConvertProcessStruct(TestPipeline):
    """_convert_process_struct 메서드 테스트"""
    
    def test_basic_conversion(self):
        """기본적인 ProcessStruct → Process 변환 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        
        # When
        process = self.pipeline._convert_process_struct(struct)
        
        # Then
        assert process.pid == 1234
        assert process.error_flags == "0b0"
        assert process.hostname == "jcode-os-1-202012180"
        assert process.binary_path == "/usr/bin/x86_64-linux-gnu-gcc-11"
        assert process.cwd == "/home/student/hw1"
        assert process.args == ["gcc", "-o", "main", "main.c"]
        assert process.exit_code == 0
    
    def test_conversion_with_korean_hostname(self):
        """한글이 포함된 hostname 변환 테스트"""
        # Given
        struct = self.create_mock_process_struct(hostname="jcode-os-학생-1")
        
        # When
        process = self.pipeline._convert_process_struct(struct)
        
        # Then
        assert process.hostname == "jcode-os-학생-1"
    
    def test_conversion_with_special_characters_in_args(self):
        """특수 문자가 포함된 args 변환 테스트"""
        # Given
        struct = self.create_mock_process_struct(
            args=["python3", "test.py", "--input", "file with spaces.txt", "--output", "결과.txt"]
        )
        
        # When
        process = self.pipeline._convert_process_struct(struct)
        
        # Then
        expected_args = ["python3", "test.py", "--input", "file with spaces.txt", "--output", "결과.txt"]
        assert process.args == expected_args
    
    def test_conversion_with_empty_args(self):
        """빈 args 변환 테스트"""
        # Given
        struct = self.create_mock_process_struct(args=[])
        
        # When
        process = self.pipeline._convert_process_struct(struct)
        
        # Then
        assert process.args == []
    
    def test_conversion_with_error_flags(self):
        """error_flags 변환 테스트"""
        # Given
        struct = self.create_mock_process_struct(error_flags=5)  # 0b101
        
        # When
        process = self.pipeline._convert_process_struct(struct)
        
        # Then
        assert process.error_flags == "0b101"


class TestLabelProcess(TestPipeline):
    """_label_process 메서드 테스트"""
    
    def test_user_binary_in_homework_directory(self):
        """hw 디렉토리 안의 사용자 바이너리 테스트"""
        # Given
        binary_path = "/home/student/hw1/main"
        args = []
        cwd = "/home/student/hw1"
        
        self.mock_classifier.classify.return_value = ProcessType.UNKNOWN
        self.mock_path_parser.parse.return_value = "hw1"
        
        # When
        process_type, homework_dir, source_file = self.pipeline._label_process(binary_path, args, cwd)
        
        # Then
        assert process_type == ProcessType.USER_BINARY
        assert homework_dir == "hw1"
        assert source_file is None
        self.mock_path_parser.parse.assert_called_once_with(binary_path)
    
    def test_gcc_compilation_with_source_file(self):
        """GCC 컴파일 with 소스파일 테스트"""
        # Given
        binary_path = "/usr/bin/x86_64-linux-gnu-gcc-11"
        args = ["gcc", "-o", "main", "main.c"]
        cwd = "/home/student/hw1"
        
        self.mock_classifier.classify.return_value = ProcessType.GCC
        self.mock_file_parser.parse.return_value = "main.c"
        self.mock_path_parser.parse.return_value = "hw1"
        
        # When
        process_type, homework_dir, source_file = self.pipeline._label_process(binary_path, args, cwd)
        
        # Then
        assert process_type == ProcessType.GCC
        assert homework_dir == "hw1"
        assert source_file == "main.c"
        self.mock_file_parser.parse.assert_called_once_with(ProcessType.GCC, args)
        # path_parser.parse는 두 번 호출됨: binary_path 확인 후, source_file 경로 확인
        assert self.mock_path_parser.parse.call_count == 2
        self.mock_path_parser.parse.assert_any_call(binary_path)
        self.mock_path_parser.parse.assert_any_call("/home/student/hw1/main.c")
    
    def test_python_execution_with_absolute_path(self):
        """Python 절대경로 실행 테스트"""
        # Given
        binary_path = "/usr/bin/python3.11"
        args = ["python3", "/home/student/hw2/test.py"]
        cwd = "/home/student"
        
        self.mock_classifier.classify.return_value = ProcessType.PYTHON
        self.mock_file_parser.parse.return_value = "/home/student/hw2/test.py"
        self.mock_path_parser.parse.return_value = "hw2"
        
        # When
        process_type, homework_dir, source_file = self.pipeline._label_process(binary_path, args, cwd)
        
        # Then
        assert process_type == ProcessType.PYTHON
        assert homework_dir == "hw2"
        assert source_file == "/home/student/hw2/test.py"
        # path_parser.parse는 두 번 호출됨: binary_path 확인 후, source_file 경로 확인
        assert self.mock_path_parser.parse.call_count == 2
        self.mock_path_parser.parse.assert_any_call(binary_path)
        self.mock_path_parser.parse.assert_any_call("/home/student/hw2/test.py")
    
    def test_compiler_without_source_file(self):
        """컴파일러이지만 소스파일 파싱 실패 테스트"""
        # Given
        binary_path = "/usr/bin/x86_64-linux-gnu-gcc-11"
        args = ["gcc", "--help"]
        cwd = "/home/student"
        
        self.mock_classifier.classify.return_value = ProcessType.GCC
        self.mock_file_parser.parse.return_value = None
        
        # When
        process_type, homework_dir, source_file = self.pipeline._label_process(binary_path, args, cwd)
        
        # Then
        assert process_type == ProcessType.GCC
        assert homework_dir is None
        assert source_file is None
    
    def test_compiler_with_source_file_outside_homework(self):
        """컴파일러이지만 소스파일이 hw 밖에 있는 경우"""
        # Given
        binary_path = "/usr/bin/x86_64-linux-gnu-gcc-11"
        args = ["gcc", "-o", "test", "test.c"]
        cwd = "/home/student"
        
        self.mock_classifier.classify.return_value = ProcessType.GCC
        self.mock_file_parser.parse.return_value = "test.c"
        self.mock_path_parser.parse.return_value = None  # hw 디렉토리가 아님
        
        # When
        process_type, homework_dir, source_file = self.pipeline._label_process(binary_path, args, cwd)
        
        # Then
        assert process_type == ProcessType.GCC
        assert homework_dir is None
        assert source_file == "test.c"
    
    def test_system_binary_unrelated_to_homework(self):
        """과제와 무관한 시스템 바이너리 테스트"""
        # Given
        binary_path = "/usr/bin/ls"
        args = ["ls", "-la"]
        cwd = "/home/student"
        
        self.mock_classifier.classify.return_value = ProcessType.UNKNOWN
        self.mock_path_parser.parse.return_value = None
        
        # When
        process_type, homework_dir, source_file = self.pipeline._label_process(binary_path, args, cwd)
        
        # Then
        assert process_type is None
        assert homework_dir is None
        assert source_file is None


class TestPipelineIntegration(TestPipeline):
    """pipeline 메서드 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_successful_event_creation(self):
        """성공적인 이벤트 생성 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        self.mock_classifier.classify.return_value = ProcessType.GCC
        self.mock_file_parser.parse.return_value = "main.c"
        self.mock_path_parser.parse.return_value = "hw1"
        
        # When
        with patch('src.pipeline.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is not None
        assert isinstance(event, Event)
        assert event.process_type == ProcessType.GCC
        assert event.homework_dir == "hw1"
        assert event.student_id == "202012180"
        assert event.class_div == "1"
        assert event.timestamp == mock_now
        assert event.source_file == "/home/student/hw1/main.c"
        assert event.exit_code == 0
        assert event.args == ["gcc", "-o", "main", "main.c"]
        assert event.cwd == "/home/student/hw1"
        assert event.binary_path == "/usr/bin/x86_64-linux-gnu-gcc-11"
    
    @pytest.mark.asyncio
    async def test_student_parsing_failure(self):
        """학생 정보 파싱 실패 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        self.mock_student_parser.parse_from_process.return_value = None
        
        # When
        event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None
    
    @pytest.mark.asyncio
    async def test_process_filtering_no_homework_dir(self):
        """과제 디렉토리가 없는 프로세스 필터링 테스트"""
        # Given
        struct = self.create_mock_process_struct(binary_path="/usr/bin/ls")
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        self.mock_classifier.classify.return_value = ProcessType.UNKNOWN
        self.mock_path_parser.parse.return_value = None
        
        # When
        event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None
    
    @pytest.mark.asyncio
    async def test_process_filtering_no_process_type(self):
        """프로세스 타입이 없는 경우 필터링 테스트"""
        # Given
        struct = self.create_mock_process_struct(binary_path="/usr/bin/unknown")
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        # _label_process가 None, None, None을 반환하도록 모킹
        with patch.object(self.pipeline, '_label_process') as mock_label:
            mock_label.return_value = (None, None, None)
            
            # When
            event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None
    
    @pytest.mark.asyncio
    async def test_absolute_source_file_handling(self):
        """절대경로 소스파일 처리 테스트"""
        # Given
        struct = self.create_mock_process_struct(
            binary_path="/usr/bin/python3.11",
            args=["python3", "/home/student/hw2/test.py"],
            cwd="/home/student"
        )
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        self.mock_classifier.classify.return_value = ProcessType.PYTHON
        self.mock_file_parser.parse.return_value = "/home/student/hw2/test.py"  # 절대경로
        self.mock_path_parser.parse.return_value = "hw2"
        
        # When
        with patch('src.pipeline.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is not None
        assert event.source_file == "/home/student/hw2/test.py"  # 절대경로 유지
    
    @pytest.mark.asyncio
    async def test_relative_source_file_handling(self):
        """상대경로 소스파일 처리 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        self.mock_classifier.classify.return_value = ProcessType.GCC
        self.mock_file_parser.parse.return_value = "main.c"  # 상대경로
        self.mock_path_parser.parse.return_value = "hw1"
        
        # When
        with patch('src.pipeline.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is not None
        assert event.source_file == "/home/student/hw1/main.c"  # 절대경로로 변환


class TestPipelineErrorHandling(TestPipeline):
    """Pipeline 오류 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_exception_in_student_parsing(self):
        """학생 파싱 중 예외 발생 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        self.mock_student_parser.parse_from_process.side_effect = Exception("Parse error")
        
        # When
        event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None
    
    @pytest.mark.asyncio
    async def test_exception_in_process_conversion(self):
        """프로세스 변환 중 예외 발생 테스트"""
        # Given
        struct = Mock()
        struct.pid = None  # 잘못된 데이터로 예외 유발
        
        # When
        event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None
    
    @pytest.mark.asyncio
    async def test_exception_in_labeling(self):
        """라벨링 중 예외 발생 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        
        with patch.object(self.pipeline, '_label_process') as mock_label:
            mock_label.side_effect = Exception("Labeling error")
            
            # When
            event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None
    
    @pytest.mark.asyncio
    async def test_exception_in_event_creation(self):
        """이벤트 생성 중 예외 발생 테스트"""
        # Given
        struct = self.create_mock_process_struct()
        student_info = StudentInfo(student_id="202012180", class_div="1")
        
        self.mock_student_parser.parse_from_process.return_value = student_info
        self.mock_classifier.classify.return_value = ProcessType.GCC
        self.mock_file_parser.parse.return_value = "main.c"
        self.mock_path_parser.parse.return_value = "hw1"
        
        # When
        with patch('src.pipeline.Event') as mock_event_class:
            mock_event_class.side_effect = Exception("Event creation error")
            
            event = await self.pipeline.pipeline(struct)
        
        # Then
        assert event is None


if __name__ == "__main__":
    pytest.main([__file__])