from prometheus_client import Counter, Histogram, Gauge
import time
import asyncio
from app.utils.logger import get_logger

# ===== 서비스 식별 =====
SERVICE_NAME = "procmon"

# ===== 파이프라인 =====
PIPELINE_EVENTS_TOTAL = Counter(
    "pipeline_events_total",
    "파이프라인에서 처리된 총 이벤트 수",
    ["result"],  # success, failure, filtered, nontarget
)

PIPELINE_DURATION_SECONDS = Histogram(
    "pipeline_duration_seconds",
    "파이프라인에서 이벤트 처리에 소요된 시간",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# ===== 수집기 =====
BPF_EVENTS_COLLECTED_TOTAL = Counter(
    "bpf_events_collected_total", 
    "BPF에서 수집된 총 이벤트 수"
)
BPF_EVENTS_LOST_TOTAL = Counter(
    "bpf_events_lost_total", 
    "BPF에서 유실된 총 이벤트 수"
)
QUEUE_EVENTS_DROPPED_TOTAL = Counter(
    "queue_events_dropped_total", 
    "큐 가득참으로 인해 드롭된 총 이벤트 수"
)
QUEUE_SIZE_CURRENT = Gauge(
    "queue_size_current", 
    "현재 처리 큐에 있는 이벤트 수"
)

# ===== 전송(API) =====
# 엔드포인트가 2개이므로 기존 라벨 유지 (method, status_code, endpoint_type)
API_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "전송된 총 API 요청 수",
    ["status_code", "endpoint_type"],
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "api_request_duration_seconds",
    "API 요청에 소요된 시간",
    ["endpoint_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ===== 하트비트(Control-plane) =====
HB_POLL_TS = Gauge(
    "poll_heartbeat_ts_seconds",
    "마지막 perf-poll 하트비트 (epoch 초)"
)
HB_LOOP_TS = Gauge(
    "loop_heartbeat_ts_seconds",
    "마지막 asyncio-loop 하트비트 (epoch 초)"
)

def poll_heartbeat_tick() -> None:
    """콜렉터 perf_buffer_poll 루프에서 호출"""
    HB_POLL_TS.set(time.time())

def loop_heartbeat_tick() -> None:
    """메인 asyncio 루프의 주기 코루틴에서 호출"""
    HB_LOOP_TS.set(time.time())

# ===== 활성 호스트 추적 =====
ACTIVE_HOSTS_CURRENT = Gauge(
    "active_hosts_current",
    "현재 활성 중인 호스트 수"
)

# TTL 기반 활성 호스트 관리
ACTIVE_HOSTS = {}  # hostname -> last_activity_time
TTL_SECONDS = 600  # 10분


# ===== BPF 메트릭 헬퍼 함수 =====
def record_bpf_event_collected() -> None:
    """BPF 이벤트 수집 시 호출"""
    BPF_EVENTS_COLLECTED_TOTAL.inc()

def record_bpf_events_lost(count: int) -> None:
    """BPF 이벤트 유실 시 호출"""
    BPF_EVENTS_LOST_TOTAL.inc(count)

def record_queue_event_dropped() -> None:
    """큐 가득참으로 이벤트 드롭 시 호출"""
    QUEUE_EVENTS_DROPPED_TOTAL.inc()

def update_queue_size(size: int) -> None:
    """현재 큐 사이즈 업데이트"""
    QUEUE_SIZE_CURRENT.set(size)

# ===== 파이프라인 메트릭 헬퍼 함수 =====
def record_pipeline_event_success() -> None:
    """파이프라인에서 이벤트 성공 처리 시 호출"""
    PIPELINE_EVENTS_TOTAL.labels(result="success").inc()

def record_pipeline_event_failure() -> None:
    """파이프라인에서 이벤트 처리 실패 시 호출"""
    PIPELINE_EVENTS_TOTAL.labels(result="failure").inc()

def record_pipeline_event_filtered() -> None:
    """파이프라인에서 이벤트 필터링 시 호출"""
    PIPELINE_EVENTS_TOTAL.labels(result="filtered").inc()

def record_pipeline_event_nontarget() -> None:
    """비대상 프로세스 이벤트 처리 시 호출"""
    PIPELINE_EVENTS_TOTAL.labels(result="nontarget").inc()

def record_pipeline_duration(seconds: float) -> None:
    """파이프라인 처리 시간 기록"""
    PIPELINE_DURATION_SECONDS.observe(seconds)

# ===== 활성 호스트 헬퍼 함수 =====
def record_host_activity(hostname: str) -> None:
    """컴파일/실행 이벤트 시 호스트 활동 기록"""
    ACTIVE_HOSTS[hostname] = time.time()

def get_active_hosts_count() -> int:
    """TTL 기반 활성 호스트 수 계산"""
    now = time.time()
    return sum(1 for last_time in ACTIVE_HOSTS.values() 
              if now - last_time <= TTL_SECONDS)

def update_active_hosts_gauge() -> None:
    """Prometheus Gauge 업데이트"""
    ACTIVE_HOSTS_CURRENT.set(get_active_hosts_count())

# ===== 하트비트 태스크 =====

async def active_hosts_update_task(period_sec: float = 60.0):
    """활성 호스트 수 업데이트 태스크"""
    logger = get_logger("metrics")
    while True:
        try:
            update_active_hosts_gauge()
        except Exception:
            logger.warning("활성 호스트 업데이트 실패", exc_info=True)
        await asyncio.sleep(period_sec)

async def loop_heartbeat_task(period_sec: float = 5.0):
    """메인 asyncio 루프의 하트비트 태스크"""
    logger = get_logger("metrics")
    while True:
        try:
            # 루프가 막히면 이 코루틴도 실행되지 않음 → 탐지 신호
            loop_heartbeat_tick()
        except Exception:
            logger.warning("루프 하트비트 갱신 실패", exc_info=True)
        await asyncio.sleep(period_sec)

# ===== API 메트릭 헬퍼 함수 =====
def record_api_request(status_code: str, endpoint_type: str) -> None:
    """API 요청 결과 기록"""
    API_REQUESTS_TOTAL.labels(status_code=status_code, endpoint_type=endpoint_type).inc()

def record_api_duration(endpoint_type: str, seconds: float) -> None:
    """API 요청 소요 시간 기록"""
    API_REQUEST_DURATION_SECONDS.labels(endpoint_type=endpoint_type).observe(seconds)