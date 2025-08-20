import asyncio
from .logger import logger
from datetime import datetime
from typing import Optional
import traceback
from .utils import convert_process_struct_to_event
from .models.event import Event
from .models.process import Process
from .models.process_type import ProcessType
from .sender import EventSender
from .classifier import ProcessClassifier
from .directory_parser import DirectoryParser
from .source_parser import SourceParser
from .student_parser import StudentParser


class ProcessEventPipeline:
    """Process를 Event로 변환하는 파이프라인"""
    
    def __init__(self, input_queue: asyncio.Queue):
        self.logger = logger
        self.input_queue = input_queue
        self.sender = EventSender()
        self.classifier = ProcessClassifier()
        self.directory_parser = DirectoryParser()
        self.source_parser = SourceParser()
        self.student_parser = StudentParser()
        
    async def start(self):
        """파이프라인 시작"""
        self.logger.info("파이프라인 시작")
        
        while True:
            try:
                # 큐에서 ProcessStruct 데이터 가져오기
                process_struct = await self.input_queue.get()
                
                # ProcessStruct -> Process 변환
                process = convert_process_struct_to_event(process_struct)
                
                # Process → Event 변환
                event = await self.process(process)
                
                if event:
                    # Sender로 전송
                    success = await self.sender.send_event(event, process)
                    if success:
                        self.logger.debug(f"이벤트 전송 성공: {process.binary_path}")
                    else:
                        self.logger.error(f"이벤트 전송 실패: {process.binary_path}")
                else:
                    self.logger.debug(f"이벤트 필터링됨: {process.binary_path}")
                
                self.input_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"파이프라인 처리 실패: {e}")
    
    async def process(self, process: Process) -> Optional[Event]:
        """Process를 Event로 변환 - 명확한 데이터 흐름"""
        now = datetime.now()
        try:
            # 1. 프로세스 분류 (독립적인 첫 번째 단계)
            classification = self.classifier.classify(process.binary_path, self.directory_parser)
            if classification.is_unknown:
                self.logger.debug(f"UNKNOWN 프로세스 타입 필터링: {process.binary_path}")
                return None
            
            # 2. 학생 정보 파싱 (독립적인 두 번째 단계)
            student_info = self.student_parser.parse_from_process(process)
            if not student_info:
                self.logger.warning(f"학생 정보 파싱 실패: {process.hostname}")
                return None
            
            # 3. 과제 컨텍스트 검증 (핵심 필터링 로직)
            is_homework_event = (classification.is_compilation 
                                 or classification.process_type == ProcessType.PYTHON 
                                 or classification.is_user_binary)

            if is_homework_event and not classification.homework_dir:
                self.logger.debug(f"[필터링-과제] 과제 디렉토리 외부의 이벤트: {process.binary_path}")
                return None
            
            # 4. 소스 파일 추출 및 관련 이벤트 필터링
            source_file = None
            is_code_event = classification.is_compilation or classification.process_type == ProcessType.PYTHON
            if is_code_event:
                source_file = self.source_parser.parse(classification.process_type, process.args)
                # 소스 파일을 못찾은 코드 이벤트는 필터링
                if not source_file:
                    self.logger.debug(f"[필터링-소스] 소스 파일을 찾을 수 없는 코드 이벤트: {process.binary_path} {process.args}")
                    return None
            
            # 5. 모든 정보가 준비된 후 Event 조립
            event = Event(
                process_type=classification.process_type,
                homework_dir=classification.homework_dir,
                student_id=student_info.student_id,
                class_div=student_info.class_div,
                timestamp=now,
                source_file=source_file
            )
            
            return event
            
        except Exception as e:
            # traceback.format_exc() 함수가 예외에 대한 상세한 스택 트레이스 정보를 문자열로 반환
            error_trace = traceback.format_exc()
            self.logger.error(f"이벤트 변환 실패: {e}\n{error_trace}")
            return None
    
