"""Watcher 애플리케이션의 예외 클래스들"""

class WatcherError(Exception):
    """Watcher 애플리케이션의 기본 예외 클래스"""
    pass

class StorageError(WatcherError):
    """스토리지 관련 예외
    
    파일 저장, 읽기, 삭제 등 스토리지 작업 중 발생하는 모든 예외
    """
    pass

class MetadataError(WatcherError):
    """메타데이터 관련 예외
    
    메타데이터 생성, 검증, 처리 중 발생하는 예외
    """
    pass

class ApiError(WatcherError):
    """API 통신 관련 예외
    
    외부 API 통신 중 발생하는 예외 (타임아웃, 연결 실패 등)
    """
    pass

class WatcherConfigError(WatcherError):
    """감시자 설정 및 초기화 관련 예외
    
    설정 파일 처리, 디렉토리 구조 검증, 감시자 초기화 등 과정에서 발생하는 예외
    """
    pass

class QueueError(WatcherError):
    """이벤트 큐 처리 관련 예외
    
    이벤트 큐 작업(추가, 제거, 대기 등) 중 발생하는 예외
    """
    pass

class ConfigError(WatcherError):
    """설정 관련 예외"""
    pass

class FileError(WatcherError):
    """파일 처리 관련 예외"""
    pass

class WatcherSetupError(WatcherError):
    """감시자 초기화 및 설정 관련 예외"""
    pass 