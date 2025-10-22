import aiohttp
import time
from app.utils.logger import get_logger
from app.utils.metrics import record_api_request, record_api_duration
from typing import Dict, Any, Optional
from app.models.event import Event
from app.models.process import Process
from app.models.process_type import ProcessType


class EventSender:
    """Event를 백엔드 API로 전송하는 클라이언트"""

    def __init__(self, base_url: str, timeout: int = 20):
        self.logger = get_logger("sender")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def send_event(self, event: Event) -> bool:
        """Event 타입에 따라 적절한 API로 전송"""
        try:
            if not self._validate_event(event):
                return False

            if event.process_type.is_execution:
                return await self._send_execution(event)
            elif event.process_type.is_compilation:
                return await self._send_compilation(event)
            else:
                self.logger.warning(
                    "알 수 없는 이벤트 타입", event_type=str(event.process_type)
                )
                return False

        except Exception as e:
            self.logger.error("이벤트 전송 실패", exc_info=True)
            return False

    def _validate_event(self, event: Event) -> bool:
        """Event 데이터 유효성 검사"""
        if not event.class_div or not event.student_id or not event.homework_dir:
            self.logger.error("필수 필드 누락: class_div, student_id, homework_dir")
            return False
        return True

    async def _send_execution(self, event: Event) -> bool:
        """실행 이벤트 전송 (USER_BINARY, PYTHON)"""
        endpoint = (
            f"/api/{event.class_div}/{event.homework_dir}/{event.student_id}/logs/run"
        )

        # PYTHON vs USER_BINARY에 따른 process_type 결정
        process_type = (
            "python" if event.process_type == ProcessType.PYTHON else "binary"
        )
        target_path = event.source_file if event.source_file else event.binary_path

        data = {
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "exit_code": event.exit_code,
            "cmdline": " ".join(event.args) if event.args else "",
            "cwd": event.cwd,
            "target_path": target_path,
            "process_type": process_type,
        }

        return await self._send_request(endpoint, data)

    async def _send_compilation(self, event: Event) -> bool:
        """컴파일 이벤트 전송 (GCC, CLANG, GPP)"""
        endpoint = (
            f"/api/{event.class_div}/{event.homework_dir}/{event.student_id}/logs/build"
        )

        data = {
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "exit_code": event.exit_code,
            "cmdline": " ".join(event.args) if event.args else "",
            "cwd": event.cwd,
            "binary_path": event.binary_path,
            "target_path": event.source_file,
        }

        return await self._send_request(endpoint, data)

    async def _send_request(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """HTTP 요청 전송"""
        start_time = time.time()
        endpoint_type = "build" if "/build" in endpoint else "run"
        
        try:
            self.logger.debug("API 요청 시작", endpoint=endpoint, data=data)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{endpoint}", json=data, timeout=self.timeout
                ) as response:
                    # API 요청 결과 메트릭 기록
                    record_api_request(str(response.status), endpoint_type)
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        self.logger.error(
                            "API 요청 실패", status=response.status, error=error_text
                        )
                        return False

                    self.logger.info("API 요청 성공", endpoint=endpoint)
                    return True

        except Exception as e:
            # 예외 발생 시에도 메트릭 기록 
            record_api_request("error", endpoint_type)
            self.logger.error("HTTP 요청 실패", endpoint=endpoint, exc_info=True)
            return False
        
        finally:
            # 성공/실패 관계없이 레이턴시 메트릭 기록
            duration = time.time() - start_time
            record_api_duration(endpoint_type, duration)
