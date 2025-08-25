import os
from .utils.logger import get_logger
from datetime import datetime
from typing import Optional, Tuple, List
import traceback
import structlog.contextvars as ctx
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

    def __init__(
        self,
        classifier: ProcessClassifier,
        path_parser: PathParser,
        file_parser: FileParser,
        student_parser: StudentParser,
    ):
        self.logger = get_logger("pipeline")
        self.classifier = classifier
        self.path_parser = path_parser
        self.file_parser = file_parser
        self.student_parser = student_parser

    async def pipeline(self, process_struct) -> Optional[Event]:
        """ProcessStruct를 Event로 변환"""

        try:
            current_timestamp = datetime.now()
            # 구조체 클래스 변환
            process = self._convert_process_struct(process_struct)

            # 학생 정보 파싱
            student_info = self.student_parser.parse_from_process(process)
            if not student_info:
                self.logger.warning("학생 정보 파싱 실패", hostname=process.hostname)
                return None

            # 사용자 정보 컨텍스트 주입
            ctx.bind_contextvars(
                student_id=student_info.student_id, class_div=student_info.class_div
            )

            # 프로세스 라벨링
            process_type, homework_dir, source_file = self._label_process(
                process.binary_path, process.args, process.cwd
            )

            # 필터링 1: 과제와 무관한 케이스들을 세분화하여 필터링
            if not process_type:
                self.logger.debug(
                    "이벤트 필터링: 비 대상 프로세스",
                    binary_path=process.binary_path,
                )
                return None

            # 필터링 2: 타깃 파일 필요 + 소스 누락
            if process_type.requires_target_file and (not source_file):
                self.logger.info(
                    "이벤트 필터링: 컴파일/실행 프로세스의 소스 파일 누락",
                    process_type=str(process_type),
                    student_id=student_info.student_id,
                    binary_path=process.binary_path,
                    args=process.args
                )
                return None
            
            # 필터링 3: 과제 디렉터리 외부
            if process_type.requires_target_file and source_file and (not homework_dir):
                self.logger.info(
                    "이벤트 필터링: 과제 디렉터리 외부 파일 컴파일/실행",
                    process_type=str(process_type),
                    student_id=student_info.student_id,
                    args=process.args,
                    source_file=source_file,
                    binary_path=process.binary_path,
                )
                return None

            # 필터링 4: 타깃 파일 불필요(유저바이너리) + 과제 디렉토리 미매칭
            if process_type.is_user_binary and not homework_dir:
                self.logger.info(
                    "이벤트 필터링: 과제 디렉터리 외 프로세스",
                    process_type=str(process_type),
                    binary_path=process.binary_path,
                    args=process.args
                )
                return None

            # 소스파일 절대경로 변환
            absolute_source_file = self._get_absolute_source_file(
                source_file, process.cwd
            )

            # 이벤트 반환
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
                binary_path=process.binary_path,
            )

            self.logger.debug(
                "이벤트 생성됨",
                process_type=str(process_type),
                homework_dir=homework_dir,
                student_id=student_info.student_id,
                source_file=absolute_source_file,
            )

            return event

        except Exception:
            self.logger.error("이벤트 변환 실패", exc_info=True)
            return None

        finally:
            ctx.clear_contextvars()

    def _label_process(
        self, binary_path: str, args: List[str], cwd: str
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
        self.logger.debug(
            "바이너리 분류 완료", binary_path=binary_path, system_type=str(system_type)
        )

        # 2) 바이너리 자체가 hw 안이면 → USER_BINARY
        binary_hw = self.path_parser.parse(binary_path)
        if binary_hw and system_type.is_unknown:
            return ProcessType.USER_BINARY, binary_hw, None

        # 3) 컴파일러/파이썬이면 대상 파일 기준으로 hw 결정
        if system_type.requires_target_file:
            source_file = self.file_parser.parse(system_type, args)
            self.logger.debug("파일 파싱 완료", args=args, source_file=source_file)
            if not source_file:
                return system_type, None, None
            full_path = (
                source_file
                if os.path.isabs(source_file)
                else os.path.join(cwd, source_file)
            )
            file_hw = self.path_parser.parse(full_path)
            self.logger.debug(
                "경로 파싱 완료", full_path=full_path, homework_dir=file_hw
            )
            if not file_hw:
                return system_type, None, source_file
            return system_type, file_hw, source_file

        # 4) 나머지는 과제와 무관
        return None, None, None

    def _get_absolute_source_file(
        self, source_file: Optional[str], cwd: str
    ) -> Optional[str]:
        """소스파일을 절대경로로 변환"""
        if not source_file:
            return None
        return (
            source_file
            if os.path.isabs(source_file)
            else os.path.join(cwd, source_file)
        )

    def _convert_process_struct(self, struct: ProcessStruct) -> Process:
        """프로세스 구조체를 Process 객체로 변환"""
        return Process(
            pid=struct.pid,
            error_flags=bin(struct.error_flags),
            hostname=struct.hostname.decode(),
            binary_path=bytes(struct.binary_path[struct.binary_path_offset :])
            .strip(b"\0")
            .decode("utf-8"),
            cwd=bytes(struct.cwd[struct.cwd_offset :]).strip(b"\0").decode("utf-8"),
            args=[
                arg.decode("utf-8", errors="replace")
                for arg in bytes(struct.args[: struct.args_len]).split(b"\0")
                if arg
            ],
            exit_code=struct.exit_code,
        )
