import os
import threading
import time
from collections import OrderedDict
from typing import Any


class BoundedTTLCache:
    """Thread-safe bounded TTL/LRU cache with explicit prefix invalidation."""

    def __init__(self, max_entries: int = 1_000):
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self.max_entries = max_entries
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                self._cache.pop(key, None)
                return None
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        if ttl <= 0:
            return
        with self._lock:
            self._purge_expired_locked()
            self._cache[key] = (time.monotonic() + ttl, value)
            self._cache.move_to_end(key)
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [key for key in self._cache if key.startswith(prefix)]:
                self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired_locked()
            return len(self._cache)

    def _purge_expired_locked(self) -> None:
        now = time.monotonic()
        for key in [key for key, (expires_at, _) in self._cache.items() if expires_at <= now]:
            self._cache.pop(key, None)


cache = BoundedTTLCache(max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "1000")))


def log_cache_key(
    kind: str,
    class_div: str,
    hw_name: str,
    student_id: int,
    from_time,
    to_time,
    limit: int,
    cursor: str | None,
) -> str:
    return ":".join(
        [
            kind,
            class_div,
            hw_name,
            str(student_id),
            str(from_time or ""),
            str(to_time or ""),
            str(limit),
            str(cursor or ""),
        ]
    )


def invalidate_log_cache(kind: str, class_div: str, hw_name: str, student_id: int) -> None:
    cache.delete_prefix(f"{kind}:{class_div}:{hw_name}:{student_id}:")
