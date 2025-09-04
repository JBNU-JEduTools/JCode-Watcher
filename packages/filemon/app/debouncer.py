import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional
from watchdog.events import FileSystemEvent
from app.utils.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

class Debouncer:
    """파일 시스템 이벤트 debounce 처리"""
    
    def __init__(self, processed_queue: asyncio.Queue):
        self.processed_queue = processed_queue
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self.in_flight: Dict[str, bool] = {}
        
    async def process_event(self, event: FileSystemEvent):
        """raw 파일시스템 이벤트를 debounce 처리"""
        try:
            key = self._generate_key(event)
            
            if event.event_type == "deleted" or event.event_type == "moved":
                await self._handle_immediate_event(key, event)
                return
            
            # modified 이벤트만 debounce 처리
            await self._add_to_bucket(key, event)
            
        except Exception as e:
            logger.error("debounce 처리 중 오류",
                        event_type=event.event_type,
                        src_path=event.src_path,
                        error_type=type(e).__name__,
                        exc_info=True)
    
    def _generate_key(self, event: FileSystemEvent) -> str:
        """이벤트로부터 debounce 키 생성 (경로 기반)"""
        if event.event_type == "moved":
            # moved는 dest_path 기준
            path = getattr(event, 'dest_path', event.src_path)
        else:
            path = event.src_path
        
        return str(Path(path))
    
    async def _handle_immediate_event(self, key: str, immediate_event: FileSystemEvent):
        """
        즉시 처리 이벤트(deleted, moved)를 처리합니다.
        규칙: 보류 중인 modified 이벤트를 먼저 플러시하고, 그 다음 즉시 처리 이벤트를 전달합니다.
        """
        if self.in_flight.get(key, False):
            logger.debug("이미 처리 중인 키 무시", key=key)
            return

        try:
            self.in_flight[key] = True

            # 1. 보류 중인 버킷을 가져와서, 그 안의 modified 이벤트를 먼저 플러시합니다.
            pending_bucket = self.buckets.pop(key, None)
            if pending_bucket:
                if pending_bucket.get('timer_task'):
                    pending_bucket['timer_task'].cancel()
                
                # 마지막 modified 이벤트를 대표로 선택하여 플러시합니다.
                representative_event = pending_bucket['events'][-1]
                await self.processed_queue.put(representative_event)
                logger.debug("보류 중인 modified 이벤트 플러시 완료", key=key)

            # 2. 수신된 즉시 처리 이벤트를 전달합니다.
            await self.processed_queue.put(immediate_event)
            logger.debug("즉시 처리 이벤트 전달 완료", key=key)

        finally:
            self.in_flight[key] = False
    
    async def _add_to_bucket(self, key: str, event: FileSystemEvent):
        """버킷에 이벤트를 추가하고 디바운스 타이머를 재설정합니다."""
        now = time.time()
        
        if key in self.buckets:
            bucket = self.buckets[key]
            
            # max_wait 체크: 너무 오래된 버킷은 강제 플러시
            if now - bucket['first_ts'] >= settings.DEBOUNCE_MAX_WAIT:
                await self._flush_bucket(key)
                # 플러시 후 새 버킷으로 시작
                self.buckets[key] = {
                    'events': [event],
                    'first_ts': now,
                    'last_ts': now,
                }
            else:
                # 기존 버킷에 이벤트 추가
                bucket['events'].append(event)
                bucket['last_ts'] = now
        else:
            # 새 버킷 생성
            self.buckets[key] = {
                'events': [event],
                'first_ts': now,
                'last_ts': now,
            }
        
        # 이벤트가 추가될 때마다 항상 타이머를 재설정 (표준 디바운스 동작)
        await self._schedule_timer(key)
    
    async def _schedule_timer(self, key: str):
        """타이머를 스케줄링하거나 재설정합니다."""
        bucket = self.buckets.get(key)
        if not bucket:
            return
            
        # 기존 타이머가 있다면 취소
        if bucket.get('timer_task'):
            bucket['timer_task'].cancel()
        
        # 새 타이머 시작
        bucket['timer_task'] = asyncio.create_task(
            self._timer_callback(key, settings.DEBOUNCE_WINDOW)
        )
    
    async def _timer_callback(self, key: str, delay: float):
        """타이머 콜백"""
        try:
            await asyncio.sleep(delay)
            await self._flush_bucket(key)
        except asyncio.CancelledError:
            # 타이머가 취소됨 (새 이벤트가 들어옴)
            pass
        except Exception as e:
            logger.error("타이머 콜백 오류",
                       key=key,
                       error_type=type(e).__name__,
                       exc_info=True)
    
    async def _flush_bucket(self, key: str):
        """버킷 플러시"""
        if self.in_flight.get(key, False):
            logger.debug("이미 처리 중인 키 무시", key=key)
            return
            
        bucket = self.buckets.pop(key, None)
        if not bucket or not bucket['events']:
            return
        
        try:
            self.in_flight[key] = True
            
            # 마지막 이벤트를 대표로 선택
            representative_event = bucket['events'][-1]
            
            await self.processed_queue.put(representative_event)
            
            logger.debug("버킷 플러시 완료",
                       key=key,
                       event_count=len(bucket['events']))
            
        finally:
            self.in_flight[key] = False