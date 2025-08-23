# 임시파일
import asyncio
from functools import wraps
import structlog

def general_activity_logger(logger, level: str = 'debug'):
    """
    메서드의 활동(실패/예외)을 로깅하는 데코레이터 팩토리.
    동기/비동기 함수를 자동으로 감지하여 처리합니다.

    Args:
        logger: 사용할 로거 객체
        level: 함수 실패 시 기록할 로그 레벨 (e.g., 'debug', 'warning')
    """
    # getattr을 사용해 logger에서 level에 해당하는 메서드를 가져옵니다.
    # 만약 'debug', 'info' 등이 아니면 기본값으로 debug를 사용합니다.
    log_func = getattr(logger, level.lower(), logger.debug)

    def decorator(func):
        # 데코레이팅할 함수가 코루틴(async def)인지 확인
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(self, *args, **kwargs):
                input_data = args[0] if args else "No input"
                try:
                    result = await func(self, *args, **kwargs)
                    if result is None:
                        log_func("작업 실패", function=func.__name__, input_data=repr(input_data))
                    return result
                except Exception as e:
                    logger.error("함수 실행 중 예외 발생", 
                               function=func.__name__, 
                               input_data=repr(input_data),
                               exc_info=True)
                    return None
            return async_wrapper
        else:
            # 일반 동기 함수인 경우
            @wraps(func)
            def sync_wrapper(self, *args, **kwargs):
                input_data = args[0] if args else "No input"
                try:
                    result = func(self, *args, **kwargs)
                    if result is None:
                        log_func("작업 실패", function=func.__name__, input_data=repr(input_data))
                    return result
                except Exception as e:
                    logger.error("함수 실행 중 예외 발생", 
                               function=func.__name__, 
                               input_data=repr(input_data),
                               exc_info=True)
                    return None
            return sync_wrapper
    return decorator