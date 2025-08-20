import ctypes

# 상수 정의
UTS_LEN = 65
MAX_PATH_LEN = 256
ARGSIZE = 256

class ProcessStruct(ctypes.Structure):
    """프로세스 커널 이벤트 구조체
    
    커널 공간과 통신하기 위한 C 구조체입니다.
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
