import time
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

# 프로메테우스 레지스트리 (REGISTRY와 다름)
filemon_registry = CollectorRegistry()

# =============================================================================
# Filemon 메트릭
# =============================================================================

# 1. Watchdog 상태 메트릭
watchdog_up = Gauge(
    'watchdog_up',
    'Watchdog Observer 스레드 상태 (1=활성, 0=중지)',
    registry=filemon_registry
)

# 2. 이벤트 처리 메트릭
watchdog_last_event_time_seconds = Gauge(
    'watchdog_last_event_time_seconds',
    '마지막으로 감지된 파일 시스템 이벤트의 Unix 타임스탬프',
    registry=filemon_registry
)

raw_events_total = Counter(
    'raw_events_total',
    '감지된 원시 파일 시스템 이벤트의 총 수',
    ['type'],
    registry=filemon_registry
)

# 3. 큐 메트릭
queue_size = Gauge(
    'queue_size',
    '현재 큐 크기 (대기 중인 이벤트 수)',
    ['queue'],
    registry=filemon_registry
)

debounced_events_total = Counter(
    'debounced_events_total',
    '디바운싱으로 인해 삭제된 총 이벤트 수',
    registry=filemon_registry
)

# 4. API 요청 메트릭
api_requests_total = Counter(
    'api_requests_total',
    '외부 서비스에 대한 총 API 요청 수',
    ['status'],
    registry=filemon_registry
)

# 5. 오류 메트릭
file_size_exceeded_total = Counter(
    'file_size_exceeded_total',
    '크기 제한 초과로 인해 건너뛴 총 파일 수',
    registry=filemon_registry
)

parse_errors_total = Counter(
    'parse_errors_total',
    '파일 경로 구문 분석 실패 총 수',
    registry=filemon_registry
)

processing_duration_seconds = Histogram(
    'processing_duration_seconds',
    '이벤트 처리 시간 (초)',
    ['component'],
    registry=filemon_registry
)

# --- Helper Functions ---

def record_raw_event(event_type: str):
    """
    A raw filesystem event was detected.
    Updates all relevant metrics for this event.
    """
    raw_events_total.labels(type=event_type).inc()
    watchdog_last_event_time_seconds.set(time.time())

def set_queue_size(queue_name: str, size: int):
    """Sets the current size for a given queue."""
    queue_size.labels(queue=queue_name).set(size)

def record_debounced_events(count: int):
    """Records that a number of events were debounced (discarded)."""
    debounced_events_total.inc(count)

def record_api_request(status: str):
    """Records an API request with its status."""
    api_requests_total.labels(status=status).inc()

def record_file_size_exceeded():
    """Records that a file was skipped due to its size."""
    file_size_exceeded_total.inc()

def record_parse_error():
    """Records a file path parsing error."""
    parse_errors_total.inc()
