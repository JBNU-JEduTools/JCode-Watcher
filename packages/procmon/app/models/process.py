from dataclasses import dataclass

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