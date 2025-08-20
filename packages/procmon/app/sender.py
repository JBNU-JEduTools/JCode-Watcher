import aiohttp
from .logger import logger
from typing import Dict, Any, Optional
from .models.event import Event
from .models.process import Process
from .models.process_type import ProcessType


class EventSender:
    """Event를 백엔드 API로 전송하는 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 20):
        self.logger = logger
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
    async def send_event(self, event: Event, process: Process) -> bool:
        """Event 타입에 따라 적절한 API로 전송"""
        try:
            if not self._validate_event(event):
                return False
                
            if event.is_execution:
                return await self._send_execution(event, process)
            elif event.is_compilation:
                return await self._send_compilation(event, process)
            else:
                self.logger.warning(f"알 수 없는 이벤트 타입: {event.process_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"이벤트 전송 실패: {repr(e)}")
            return False
    
    def _validate_event(self, event: Event) -> bool:
        """Event 데이터 유효성 검사"""
        if not event.class_div or not event.student_id or not event.homework_dir:
            self.logger.error("필수 필드 누락: class_div, student_id, homework_dir")
            return False
        return True
    
    async def _send_execution(self, event: Event, process: Process) -> bool:
        """실행 이벤트 전송 (USER_BINARY, PYTHON)"""
        endpoint = f"/api/{event.class_div}/{event.homework_dir}/{event.student_id}/logs/run"
        
        # PYTHON vs USER_BINARY에 따른 process_type 결정
        process_type = "python" if event.process_type == ProcessType.PYTHON else "binary"
        target_path = event.source_file if event.source_file else process.binary_path
        
        data = {
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'exit_code': process.exit_code,
            'cmdline': process.args,
            'cwd': process.cwd,
            'target_path': target_path,
            'process_type': process_type
        }
        
        return await self._send_request(endpoint, data)
    
    async def _send_compilation(self, event: Event, process: Process) -> bool:
        """컴파일 이벤트 전송 (GCC, CLANG, GPP)"""
        endpoint = f"/api/{event.class_div}/{event.homework_dir}/{event.student_id}/logs/build"
        
        data = {
            'timestamp': event.timestamp.isoformat() if event.timestamp else None,
            'exit_code': process.exit_code,
            'cmdline': process.args,
            'cwd': process.cwd,
            'binary_path': process.binary_path,
            'target_path': event.source_file
        }
        
        return await self._send_request(endpoint, data)
    
    async def _send_request(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """HTTP 요청 전송"""
        try:
            self.logger.debug(f"API 요청: {endpoint}, 데이터: {data}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{self.base_url}{endpoint}',
                    json=data,
                    timeout=self.timeout
                ) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        self.logger.error(f"API 실패: status={response.status}, error={error_text}")
                        return False
                        
                    self.logger.info(f"API 성공: {endpoint}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"HTTP 요청 실패: {endpoint}, error={repr(e)}")
            return False