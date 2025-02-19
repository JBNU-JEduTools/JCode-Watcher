"""예외 정의

애플리케이션에서 사용되는 예외 클래스들을 정의합니다.
"""

class ConfigError(Exception):
    """설정 및 환경 관련 오류
    
    설정값이 유효하지 않거나 필수 설정이 누락된 경우,
    또는 파일 시스템 접근 권한 등 환경 설정 관련 오류가 발생한 경우
    발생하는 오류입니다.
    """

class ApiError(Exception):
    """API 통신 관련 예외
    
    API 서버와의 통신 중 발생하는 오류입니다.
    예: 연결 실패, 타임아웃, 인증 실패 등
    """

class InvalidHomeworkPathError(Exception):
    """과제 경로 형식 오류
    
    과제 파일 경로가 지정된 형식과 일치하지 않는 경우 발생하는 오류입니다.
    예상되는 경로 형식: /watcher/codes/{과목-분반-학번}/config/workspace/{과제번호}/{파일명}
    예시: /watcher/codes/os-3-202012180/config/workspace/hw1/main.c
    """