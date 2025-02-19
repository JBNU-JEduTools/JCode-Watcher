"""예외 정의

애플리케이션에서 사용되는 예외 클래스들을 정의합니다.
"""

class WatcherError(Exception):
    """기본 예외 클래스
    
    모든 워처 관련 예외의 기본 클래스입니다.
    """
    
    def __init__(self, message: str, cause: Exception = None):
        """
        Args:
            message: 예외 메시지
            cause: 원인이 된 예외 (선택사항)
        """
        super().__init__(message)
        self.cause = cause
        
    def __str__(self) -> str:
        if self.cause:
            return f"{super().__str__()} (원인: {self.cause})"
        return super().__str__()

class ConfigurationError(WatcherError):
    """설정 관련 예외
    
    설정값이 유효하지 않거나 필수 설정이 누락된 경우 발생
    """

class QueueError(WatcherError):
    """큐 관련 예외
    
    이벤트 큐 작업 중 오류가 발생한 경우
    """

class QueueFullError(QueueError):
    """큐 포화 예외
    
    이벤트 큐가 가득 찬 경우 발생
    """

class SnapshotError(WatcherError):
    """스냅샷 관련 예외
    
    스냅샷 생성이나 관리 중 오류가 발생한 경우
    """

class ApiError(WatcherError):
    """API 통신 관련 예외
    
    API 서버와의 통신 중 오류가 발생한 경우
    """

class FileNotFoundInWorkspaceError(WatcherError):
    """작업 공간 파일 누락 예외
    
    필요한 파일이나 디렉토리를 찾을 수 없는 경우 발생
    """

class InvalidHomeworkPathError(WatcherError):
    """과제 경로 형식 오류
    
    과제 파일 경로가 예상된 형식과 일치하지 않는 경우 발생
    예: 잘못된 과목 코드, 과제 번호 누락, 잘못된 경로 구조 등
    """ 