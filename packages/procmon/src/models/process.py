import ctypes
from dataclasses import dataclass

# 상수 정의
UTS_LEN = 65
MAX_PATH_LEN = 256
ARGSIZE = 256

def convert_process_struct_to_event(struct: 'ProcessStruct') -> 'Process':
    """프로세스 구조체를 Process 객체로 변환"""
    return Process(
        pid=struct.pid,
        error_flags=bin(struct.error_flags),
        hostname=struct.hostname.decode(),
        binary_path=bytes(struct.binary_path[struct.binary_path_offset:]).strip(b'\0').decode('utf-8'),
        cwd=bytes(struct.cwd[struct.cwd_offset:]).strip(b'\0').decode('utf-8'),
        args=' '.join(arg.decode('utf-8', errors='replace') 
                     for arg in bytes(struct.args[:struct.args_len]).split(b'\0') if arg),
        exit_code=struct.exit_code
    )

class ProcessStruct(ctypes.Structure):
    """프로세스 커널 이벤트 구조체
    
    커널 공간과 통신하기 위한 C 구조체입니다.
    이 구조체는 직접 수정하지 말고, 항상 Process를 통해 접근하세요.
    """
    _fields_ = [
        ("pid", ctypes.c_uint32),                     # 4 bytes
        ("error_flags", ctypes.c_uint32),             # 4 bytes
        ("hostname", ctypes.c_char * UTS_LEN),        # 65 bytes
        ("binary_path", ctypes.c_ubyte * MAX_PATH_LEN),  # 256 bytes
        ("cwd", ctypes.c_ubyte * MAX_PATH_LEN),         # 256 bytes
        ("args", ctypes.c_ubyte * ARGSIZE),             # 256 bytes
        ("binary_path_offset", ctypes.c_int),         # 4 bytes
        ("cwd_offset", ctypes.c_int),                 # 4 bytes
        ("args_len", ctypes.c_uint32),                # 4 bytes
        ("exit_code", ctypes.c_int)                   # 4 bytes
    ]                                                 # 총 857 bytes

    def to_event(self) -> 'Process':
        """구조체를 이벤트 객체로 변환"""
        return convert_process_struct_to_event(self)

@dataclass(frozen=True)
class Process:
    """프로세스 기본 데이터 클래스
    
    커널 공간의 ProcessStruct를 파이썬 친화적인 형태로 변환한 클래스입니다.
    이 클래스는 커널에서 받은 원시 데이터를 나타내며, 불변 객체입니다.
    """
    pid: int                # 프로세스 ID
    binary_path: str        # 실행 파일 경로
    cwd: str               # 작업 디렉토리
    args: str              # 명령줄 인자
    error_flags: str       # 프로세스 수집 에러 플래그
    exit_code: int         # 프로세스 종료 코드
    hostname: str          # 호스트 이름 (예: "jcode-os-1-202012180-hash")