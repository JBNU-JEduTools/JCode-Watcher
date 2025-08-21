import os
from .utils.logger import logger
from datetime import datetime
from typing import Optional, Tuple, List
import traceback
from .models.event import Event
from .models.process import Process
from .models.process_struct import ProcessStruct
from .models.process_type import ProcessType
from .classifier import ProcessClassifier
from .path_parser import PathParser
from .file_parser import FileParser
from .student_parser import StudentParser



class Pipeline:
    """Process를 Event로 변환하는 파이프라인"""
    
    def __init__(self, 
                 classifier: ProcessClassifier,
                 path_parser: PathParser,
                 file_parser: FileParser,
                 student_parser: StudentParser):
        self.logger = logger
        self.classifier = classifier
        self.path_parser = path_parser
        self.file_parser = file_parser
        self.student_parser = student_parser
        
    def _convert_process_struct(self, struct: ProcessStruct) -> Process:
        """프로세스 구조체를 Process 객체로 변환"""
        return Process(
            pid=struct.pid,
            error_flags=bin(struct.error_flags),
            hostname=struct.hostname.decode(),
            binary_path=bytes(struct.binary_path[struct.binary_path_offset:]).strip(b'\0').decode('utf-8'),
            cwd=bytes(struct.cwd[struct.cwd_offset:]).strip(b'\0').decode('utf-8'),
            args=[arg.decode('utf-8', errors='replace') 
                  for arg in bytes(struct.args[:struct.args_len]).split(b'\0') if arg],
            exit_code=struct.exit_code
        )
    
    async def pipeline(self, process_struct) -> Optional[Event]:
        """ProcessStruct를 Event로 변환 - 명확한 데이터 흐름"""

        try:
            # 시간
            current_timestamp = datetime.now()

            # ProcessStruct -> Process 변환
            process = self._convert_process_struct(process_struct)
            
            # 학생 정보 파싱
            student_info = self.student_parser.parse_from_process(process)
            if not student_info:
                self.logger.warning(f"학생 정보 파싱 실패: {process.hostname}")
                return None
            
            # 프로세스 라벨링 - 타입, 과제 디렉토리, 소스파일 결정 & 필터링
            process_type, homework_dir, source_file = self._label_process(
                process.binary_path, 
                process.args, 
                process.cwd
            )
            
            # 과제와 무관한 프로세스는 필터링
            if not process_type or not homework_dir:
                log_msg = f"[필터링] 과제와 무관한 프로세스 - 바이너리: {process.binary_path}, 작업경로: {process.cwd}, 인자: {process.args}"
                if source_file:
                    absolute_source_file = source_file if os.path.isabs(source_file) else os.path.join(process.cwd, source_file)
                    log_msg += f", 대상 소스 파일: {absolute_source_file}"
                else:
                    log_msg += f", 대상 소스 파일: 없음 (process_type={process_type}, homework_dir={homework_dir})"
                self.logger.debug(log_msg)
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
                timestamp=current_timestamp,
                source_file=absolute_source_file,
                exit_code=process.exit_code,
                args=process.args,
                cwd=process.cwd,
                binary_path=process.binary_path
            )
            
            self.logger.info(f"[이벤트 생성] 타입: {process_type}, 과제: {homework_dir}, 학생: {student_info.student_id}, 소스파일: {absolute_source_file}")
            
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
        self.logger.debug(f"[라벨링] 바이너리 분류 - 경로: {binary_path}, 타입: {system_type}")

        # 2) 바이너리 자체가 hw 안이면 → USER_BINARY
        binary_hw = self.path_parser.parse(binary_path)
        if binary_hw and system_type.is_unknown:
            return ProcessType.USER_BINARY, binary_hw, None

        # 3) 컴파일러/파이썬이면 대상 파일 기준으로 hw 결정
        if system_type.requires_target_file:
            source_file = self.file_parser.parse(system_type, args)
            self.logger.debug(f"[라벨링] 파일 파싱 - 인자: '{args}', 파싱된 소스파일: '{source_file}'")
            if not source_file:
                return system_type, None, None
            full_path = source_file if os.path.isabs(source_file) else os.path.join(cwd, source_file)
            file_hw = self.path_parser.parse(full_path)
            self.logger.debug(f"[라벨링] 경로 파싱 - 전체경로: '{full_path}', 과제디렉토리: '{file_hw}'")
            if not file_hw:
                return system_type, None, source_file
            return system_type, file_hw, source_file

        # 4) 나머지는 과제와 무관
        return None, None, None