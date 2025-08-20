"""프로메테우스 메트릭 서버

프로메테우스 메트릭 페이지를 노출하는 서버를 구현합니다.
"""

import threading
from prometheus_client import start_http_server
from src.utils.logging import get_logger
from src.config.settings import settings

class PrometheusMetrics:
    """프로메테우스 메트릭 서버 클래스"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
    def _run_metrics_server(self):
        """메트릭 서버 실행"""
        try:
            self.logger.info(f"[프로메테우스] 메트릭 서버 시작 (포트: {settings.prometheus_port})")
            start_http_server(settings.prometheus_port)
        except Exception as e:
            self.logger.error(f"[프로메테우스] 메트릭 서버 시작 실패: {e}")
            raise
        
    def start_metrics_server(self):
        """메트릭 서버를 데몬 쓰레드로 시작"""
        metrics_thread = threading.Thread(
            target=self._run_metrics_server,
            daemon=True,
            name="prometheus-metrics-server"
        )
        metrics_thread.start() 