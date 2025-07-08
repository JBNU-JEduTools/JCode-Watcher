from typing import Dict, List
from .types import ProcessType
from ..config.settings import settings
from ..homework.checker import HomeworkChecker
from ..utils.logging import get_logger
import re
from ..events.models import ProcessTypeInfo

class ProcessFilter:
    """프로세스 타입 결정"""
    def __init__(self, homework_checker: HomeworkChecker):
        self.logger = get_logger(__name__)
        self.patterns: Dict[ProcessType, List[str]] = {
            ProcessType[k]: v for k, v in settings.PROCESS_PATTERNS.items()
        }
        self.hw_checker = homework_checker
        self.logger.info(f"[ProcessFilter] 초기화 완료 - 패턴: {self.patterns}")

    def get_process_type(self, binary_path: str) -> ProcessType:
        """실행된 프로세스의 타입을 결정

        Args:
            binary_path: 실행 파일의 절대 경로
                예시: "/usr/lib/llvm-18/bin/clang" (컴파일러)
                예시: "/home/coder/project/hw1/a.out" (과제 실행 파일)
                예시: "/usr/bin/ls" (기타 프로세스)

        Returns:
            ProcessType:
                - GCC: gcc 컴파일러 실행 시
                - CLANG: clang 컴파일러 실행 시
                - PYTHON: python 인터프리터 실행 시
                - USER_BINARY: 과제 디렉토리 내 실행 파일 실행 시
                - UNKNOWN: 그 외 모든 경우

        Note:
            1. 시스템 바이너리 체크 -> 과제 실행 파일 체크 -> UNKNOWN 순으로 검사
            2. 과제 디렉토리는 '/home/coder/project/hw*' 형식이어야 함
        """
        try:
            # 1. 시스템 바이너리 (컴파일러/인터프리터) 체크
            for proc_type, patterns in self.patterns.items():
                if any(pattern in binary_path for pattern in patterns):
                    self.logger.debug(
                        f"[ProcessFilter] 시스템 프로세스 감지: "
                        f"type={proc_type.name}, "
                        f"path={binary_path}"
                    )
                    return proc_type

            # 2. 과제 디렉토리 내 실행 파일 체크
            if hw_dir := self.hw_checker.get_homework_info(binary_path):
                self.logger.debug(
                    f"[ProcessFilter] 과제 실행 파일 감지: "
                    f"path={binary_path}, "
                    f"hw_dir={hw_dir}"
                )
                return ProcessType.USER_BINARY

            # 3. 그 외는 무시
            self.logger.debug(f"[ProcessFilter] 무시된 프로세스: {binary_path}")
            return ProcessType.UNKNOWN
            
        except Exception as e:
            self.logger.error(f"[ProcessFilter] 프로세스 타입 결정 실패: {str(e)}")
            return ProcessType.UNKNOWN 