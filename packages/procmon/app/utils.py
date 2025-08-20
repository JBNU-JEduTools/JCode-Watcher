
from .models import Process, ProcessStruct


def convert_process_struct_to_event(struct: ProcessStruct) -> Process:
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