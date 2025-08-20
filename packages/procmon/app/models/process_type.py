from enum import Enum, auto


class ProcessType(Enum):
    """지원하는 프로세스 타입"""
    UNKNOWN = auto()
    GCC = auto()
    CLANG = auto()
    GPP = auto()
    PYTHON = auto()   
    USER_BINARY=auto()