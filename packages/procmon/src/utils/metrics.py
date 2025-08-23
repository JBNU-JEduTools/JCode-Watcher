from prometheus_client import Counter, Histogram, Gauge
import time

# 파이프라인 메트릭
PIPELINE_EVENTS_TOTAL = Counter(
    "pipeline_events_total",
    "파이프라인에서 처리된 총 이벤트 수",
    ["result"],  # success, failure, filtered
)

PIPELINE_DURATION_SECONDS = Histogram(
    "pipeline_duration_seconds",
    "파이프라인에서 이벤트 처리에 소요된 시간",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# 수집기 메트릭
BPF_EVENTS_COLLECTED_TOTAL = Counter(
    "bpf_events_collected_total", "BPF에서 수집된 총 이벤트 수"
)

BPF_EVENTS_LOST_TOTAL = Counter("bpf_events_lost_total", "BPF에서 유실된 총 이벤트 수")

QUEUE_EVENTS_DROPPED_TOTAL = Counter(
    "queue_events_dropped_total", "큐 가득참으로 인해 드롭된 총 이벤트 수"
)

QUEUE_SIZE_CURRENT = Gauge("queue_size_current", "현재 처리 큐에 있는 이벤트 수")

# 전송 메트릭
API_REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "전송된 총 API 요청 수",
    [
        "method",
        "status_code",
        "endpoint_type",
    ],  # GET/POST, 200/400/500, execution/compilation
)

API_REQUEST_DURATION_SECONDS = Histogram(
    "api_request_duration_seconds",
    "API 요청에 소요된 시간",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# 하트비트 메트릭 (Control-plane 모니터링)
HB_POLL_TS = Gauge(
    "procmon_poll_heartbeat_ts_seconds",
    "마지막 perf-poll 하트비트 (epoch 초)",
)
HB_POLL_SEQ = Counter(
    "procmon_poll_heartbeat_seq_total",
    "Perf-poll 하트비트 틱 수",
)

HB_LOOP_TS = Gauge(
    "procmon_loop_heartbeat_ts_seconds",
    "마지막 asyncio-loop 하트비트 (epoch 초)",
)
HB_LOOP_SEQ = Counter(
    "procmon_loop_heartbeat_seq_total",
    "Asyncio-loop 하트비트 틱 수",
)


def poll_heartbeat_tick() -> None:
    """콜렉터 perf_buffer_poll 루프에서 호출"""
    HB_POLL_TS.set(time.time())
    HB_POLL_SEQ.inc()


def loop_heartbeat_tick() -> None:
    """메인 asyncio 루프의 주기 코루틴에서 호출"""
    HB_LOOP_TS.set(time.time())
    HB_LOOP_SEQ.inc()

