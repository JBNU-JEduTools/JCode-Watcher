import aiohttp
import logging
from typing import Dict, Any
from ..config.settings import settings
from ..events.models import Event

class APIClient:
    """API 클라이언트"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = settings.api_endpoint.rstrip('/')

    async def _send_event(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """이벤트 전송 공통 로직"""
        try:
            self.logger.debug(f"API 요청 시작: {endpoint}")
            self.logger.debug(f"API 요청 데이터: {data}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}{endpoint}',
                    json=data,
                    timeout=settings.api_timeout
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        self.logger.error(f"API 실패: status={response.status}, endpoint={endpoint}, error={error_text}")
                        return False
                    self.logger.info(f"API 성공: endpoint={endpoint}")
                    return True

        except Exception as e :
            self.logger.error(f"API 오류 : endpoint={endpoint}, error={repr(e)}")
            # self.logger.exception(f"API 오류: endpoint={endpoint}")
            return False

    async def send_binary_execution(self, event: Event) -> bool:
        """실행 이벤트 전송"""
        endpoint = f"/api/{event.metadata.class_div}/{event.homework.homework_dir}/{event.metadata.student_id}/logs/run"
        
        data = {
            'timestamp': event.metadata.timestamp.isoformat(),
            'exit_code': event.base.exit_code,
            'cmdline': event.base.args,
            'cwd': event.base.cwd,
            'target_path': event.base.binary_path,
            'process_type': 'binary'
        }
        return await self._send_event(endpoint, data)

    async def send_python_execution(self, event: Event) -> bool:
        """파이썬 실행 이벤트 전송"""
        endpoint = f"/api/{event.metadata.class_div}/{event.homework.homework_dir}/{event.metadata.student_id}/logs/run"
        
        data = {
            'timestamp': event.metadata.timestamp.isoformat(),
            'exit_code': event.base.exit_code,
            'cmdline': event.base.args,
            'cwd': event.base.cwd,
            'target_path': event.homework.source_file,
            'process_type': 'python'
        }
        return await self._send_event(endpoint, data)

    async def send_compilation(self, event: Event) -> bool:
        """컴파일 이벤트 전송"""
        endpoint = f"/api/{event.metadata.class_div}/{event.homework.homework_dir}/{event.metadata.student_id}/logs/build"
        
        data = {
            'timestamp': event.metadata.timestamp.isoformat(),
            'exit_code': event.base.exit_code,
            'cmdline': event.base.args,
            'cwd': event.base.cwd,
            'binary_path': event.base.binary_path,
            'target_path': event.homework.source_file
        }
        return await self._send_event(endpoint, data) 