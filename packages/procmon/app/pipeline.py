import os
from .logger import logger
from datetime import datetime
from typing import Optional, Tuple, List
import traceback
from .utils import convert_process_struct_to_event
from .models.event import Event
from .models.process_type import ProcessType
from .classifier import ProcessClassifier
from .path_parser import PathParser
from .file_parser import FileParser
from .student_parser import StudentParser



class ProcessEventPipeline:
    """Process를 Event로 변환하는 파이프라인"""
    
    def __init__(self):
        self.logger = logger
        self.classifier = ProcessClassifier()
        self.path_parser = PathParser()
        self.file_parser = FileParser()
        self.student_parser = StudentParser()
        
    
    async def pipeline(self, process_struct) -> Optional[Event]:
        """ProcessStruct를 Event로 변환 - 명확한 데이터 흐름"""

        try:
            now = datetime.now()

            # ProcessStruct -> Process 변환
            process = convert_process_struct_to_event(process_struct)
            
            # 프로세스 라벨링 - 타입, 과제 디렉토리, 소스파일 결정
            process_type, homework_dir, source_file = self._label_process(
                process.binary_path, 
                process.args, 
                process.cwd
            )
            
            # 과제와 무관한 프로세스는 필터링
            if not process_type or not homework_dir:
                self.logger.debug(f"[필터링] 과제와 무관한 프로세스: {process.binary_path}")
                return None
            
            # 학생 정보 파싱
            student_info = self.student_parser.parse_from_process(process)
            if not student_info:
                self.logger.warning(f"학생 정보 파싱 실패: {process.hostname}")
                return None
            
            # source_file을 절대 경로로 변환
            absolute_source_file = None
            if source_file:
                absolute_source_file = source_file if os.path.isabs(source_file) else os.path.join(process.cwd, source_file)
            
            # 4. 모든 정보가 준비된 후 Event 조립
            event = Event(
                process_type=process_type,
                homework_dir=homework_dir,
                student_id=student_info.student_id,
                class_div=student_info.class_div,
                timestamp=now,
                source_file=absolute_source_file,
                exit_code=process.exit_code,
                args=process.args,
                cwd=process.cwd,
                binary_path=process.binary_path
            )
            
            return event
            
        except Exception as e:
            # traceback.format_exc() 함수가 예외에 대한 상세한 스택 트레이스 정보를 문자열로 반환
            error_trace = traceback.format_exc()
            self.logger.error(f"이벤트 변환 실패: {e}\n{error_trace}")
            return None
    
    def _label_process(
        self,
        binary_path: str, 
        args: List[str], 
        cwd: str
    ) -> Tuple[Optional[ProcessType], Optional[str], Optional[str]]:
        """Process의 타입과 과제 디렉토리를 결정하는 라벨링 함수
        
        Args:
            binary_path: 실행 바이너리의 절대 경로
            args: 프로세스 실행 인자 리스트
            cwd: 프로세스의 현재 작업 디렉토리
            
        Returns:
            Tuple[ProcessType | None, homework_dir | None, source_file | None]:
                - ProcessType: 결정된 프로세스 타입 (과제와 무관하면 None)
                - homework_dir: 과제 디렉토리 경로 (없으면 None)
                - source_file: 소스 파일 경로 (컴파일/Python이 아니면 None)
        """
        # 1) 시스템 정체성은 고정값(불변)
        system_type = self.classifier.classify(binary_path)

        # 2) 바이너리 자체가 hw 안이면 → USER_BINARY
        binary_hw = self.path_parser.parse(binary_path)
        if binary_hw and system_type.is_unknown:
            return ProcessType.USER_BINARY, binary_hw, None

        # 3) 컴파일러/파이썬이면 대상 파일 기준으로 hw 결정
        if system_type in (ProcessType.GCC, ProcessType.GPP, ProcessType.CLANG, ProcessType.PYTHON):
            source_file = self.file_parser.parse(system_type, args)
            if not source_file:
                return None, None
            full_path = source_file if os.path.isabs(source_file) else os.path.join(cwd, source_file)
            file_hw = self.path_parser.parse(full_path)
            if not file_hw:
                return None, None
            return system_type, file_hw, source_file

        # 4) 나머지는 과제와 무관
        return None, None, None