from prometheus_client import start_http_server
from old.utils.logger import get_logger
from old.config.settings import METRICS_PORT
import threading

logger = get_logger(__name__)

class MetricsManager:
    """프로메테우스 메트릭을 관리하는 클래스"""
    
    def __init__(self):
        self.port = METRICS_PORT
        
        # TODO: 추후 메트릭 구현
        # self.event_counter = Counter(
        #     'watcher_events_total',
        #     'Total number of file events',
        #     ['event_type', 'class_div', 'hw_name']
        # )
        # 
        # self.file_size_gauge = Gauge(
        #     'watcher_file_size_bytes',
        #     'Current file size in bytes',
        #     ['class_div', 'hw_name', 'filename']
        # )
        # 
        # self.event_processing_time = Histogram(
        #     'watcher_event_processing_seconds',
        #     'Time spent processing events',
        #     ['event_type']
        # )
        # 
        # self.queue_size = Gauge(
        #     'watcher_event_queue_size',
        #     'Current number of events in the queue'
        # )
    
    def _run_server(self):
        """메트릭 서버 실행"""
        try:
            start_http_server(self.port)
            logger.info(f"✅ Prometheus metrics available at http://localhost:{self.port}/metrics")
        except Exception as e:
            logger.error(f"메트릭 서버 시작 실패 - 포트: {self.port}, 오류: {str(e)}")
            raise
    
    def start_server(self):
        """메트릭 서버를 별도 스레드에서 시작"""
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
    
    # TODO: 추후 메트릭 수집 메서드 구현
    # def record_event(self, event_type: str, class_div: str, hw_name: str):
    #     pass
    # 
    # def update_file_size(self, class_div: str, hw_name: str, filename: str, size: float):
    #     pass
    # 
    # def observe_processing_time(self, event_type: str, duration: float):
    #     pass
    # 
    # def update_queue_size(self, size: int):
    #     pass 