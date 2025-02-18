"""Watcher 애플리케이션의 예외 클래스들"""

class WatcherError(Exception):
    """Watcher 애플리케이션의 기본 예외 클래스"""
    pass

class StorageError(WatcherError):
    """스토리지 관련 예외"""
    pass

class MetadataError(WatcherError):
    """메타데이터 관련 예외"""
    pass

class ApiError(WatcherError):
    """API 통신 관련 예외"""
    pass

class WatcherConfigError(WatcherError):
    """감시자 설정 관련 예외"""
    pass

class FileWatcherError(WatcherError):
    """파일 감시 관련 예외"""
    pass

class QueueError(WatcherError):
    """이벤트 큐 처리 관련 예외"""
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