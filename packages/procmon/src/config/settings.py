from typing import Dict, List, Set
import os


class Settings:
    """애플리케이션 설정

    모든 환경 변수와 상수 기반 설정을 중앙 집중적으로 관리합니다.
    """

    # 프로세스 바이너리 경로 패턴
    # process/filter.py에서 프로세스 타입 판별에 사용
    PROCESS_PATTERNS: Dict[str, List[str]] = {
        "GCC": ["/usr/bin/x86_64-linux-gnu-gcc-13", "/usr/bin/x86_64-linux-gnu-gcc-12"],
        "CLANG": [
            "/usr/lib/llvm-13/bin/clang",
            "/usr/lib/llvm-12/bin/clang",
        ],
        "GPP": [
            "/usr/bin/x86_64-linux-gnu-g++-13",
            "/usr/bin/x86_64-linux-gnu-g++-12",
        ],
        "PYTHON": [
            "/usr/bin/python3.13",
            "/usr/bin/python3.12",
            "/usr/bin/python3.11",
            "/usr/bin/python3.10",
            "/usr/bin/python3.9",
            "/usr/bin/python3.8",
            "/usr/bin/python3.7",
        ],
    }

    # 컴파일러 파싱 관련 상수
    # parser/compiler.py에서 소스 파일 추출 시 무시할 옵션들
    COMPILER_SKIP_OPTIONS: Set[str] = {
        "-o",  # 출력 파일 지정
        "-I",  # 헤더 파일 검색 경로
        "-include",  # 강제 include 파일
        "-D",  # 매크로 정의
        "-U",  # 매크로 해제
        "-MF",  # 의존성 파일 지정
    }

    def __init__(self):
        # API 설정
        self.api_endpoint = os.getenv("API_ENDPOINT", "http://localhost:8000")
        self.api_timeout = int(os.getenv("API_TIMEOUT", "20"))

        # 로깅 설정
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

        # 프로메테우스 설정
        self.prometheus_port = int(os.getenv("PROMETHEUS_PORT", "9090"))


# 싱글톤 인스턴스 생성
settings = Settings()
