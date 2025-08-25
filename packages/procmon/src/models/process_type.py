from enum import Enum, auto


class ProcessType(Enum):
    """지원하는 프로세스 타입"""

    UNKNOWN = auto()
    GCC = auto()
    CLANG = auto()
    GPP = auto()
    PYTHON = auto()
    USER_BINARY = auto()

    @property
    def is_unknown(self) -> bool:
        """UNKNOWN 타입 여부"""
        return self == ProcessType.UNKNOWN

    @property
    def is_user_binary(self) -> bool:
        """USER_BINARY 타입 여부"""
        return self == ProcessType.USER_BINARY

    @property
    def is_compilation(self) -> bool:
        """컴파일 프로세스 여부"""
        return self in (ProcessType.GCC, ProcessType.CLANG, ProcessType.GPP)

    @property
    def is_python(self) -> bool:
        """Python 타입 여부"""
        return self == ProcessType.PYTHON

    @property
    def is_execution(self) -> bool:
        """실행 프로세스 여부 (USER_BINARY, PYTHON)"""
        return self in (ProcessType.USER_BINARY, ProcessType.PYTHON)

    @property
    def requires_target_file(self) -> bool:
        return self in (
            ProcessType.GCC,
            ProcessType.GPP,
            ProcessType.CLANG,
            ProcessType.PYTHON,
        )

    @property
    def is_active_work(self) -> bool:
        """활성 작업(컴파일/실행) 프로세스 여부 - 호스트 활동 추적용"""
        return self in (
            ProcessType.GCC,
            ProcessType.CLANG,
            ProcessType.GPP,
            ProcessType.PYTHON,
            ProcessType.USER_BINARY,
        )
