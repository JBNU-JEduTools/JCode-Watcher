from typing import Any, Dict, Optional, Callable
import time
from functools import wraps
from sqlmodel import Session

class InMemoryCache:
    """
    간단한 인메모리 캐싱 구현
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값을 가져옵니다.
        만료된 경우 None을 반환합니다.
        """
        if key not in self._cache:
            # print(f"[Cache Miss] {key}")
            return None
        
        cache_data = self._cache[key]
        if cache_data["expires_at"] < time.time():
            # print(f"[Cache Expired] {key}")
            del self._cache[key]
            return None
        
        print(f"[Cache Hit] {key}")
        return cache_data["value"]
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        # print(f"[Cache Set] {key} -> {value}")
        """
        캐시에 값을 저장합니다.
        ttl은 초 단위로, 기본값은 5분(300초)입니다.
        """
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
    
    def delete(self, key: str) -> None:
        """
        캐시에서 값을 삭제합니다.
        """
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """
        모든 캐시를 삭제합니다.
        """
        self._cache.clear()

# 전역 캐시 인스턴스
cache = InMemoryCache()

def cached(ttl: int = 300):
    """
    함수 결과를 캐싱하는 데코레이터
    
    사용 예:
    @cached(ttl=600)
    def expensive_function(param1, param2):
        # 시간이 오래 걸리는 작업
        return result
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성 (함수 이름 + 인자)
            filtered_args = tuple(
                arg for arg in args if not isinstance(arg, Session)
            )
            key = f"{func.__name__}:{str(filtered_args)}:{str(kwargs)}"
            
            # 캐시에서 결과 가져오기
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # 캐시에 없으면 함수 실행
            result = func(*args, **kwargs)
            
            # 결과 캐싱
            cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator