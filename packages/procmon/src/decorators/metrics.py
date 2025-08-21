# metrics.py (별도 파일로 분리)
from functools import wraps
import time

# (메트릭 객체들이 여기에 정의됨)
# PIPELINE_PROCESSED_TOTAL = Counter('pipeline_processed_total', '...', ['result'])
# PIPELINE_DURATION_SECONDS = Histogram(...)

def measure_pipeline_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            # 원래 함수(핵심 로직) 호출
            result_event = await func(*args, **kwargs)

            # 결과에 따라 메트릭 분기 처리
            if result_event is None:
                # 여기서 더 상세한 분기가 가능하지만, 간단하게 '실패'로 처리
                PIPELINE_PROCESSED_TOTAL.labels(result='failure').inc()
            else:
                PIPELINE_PROCESSED_TOTAL.labels(result='success').inc()

            return result_event
        except Exception:
            PIPELINE_PROCESSED_TOTAL.labels(result='error').inc()
            # 예외를 다시 발생시켜 상위 핸들러가 처리하도록 함
            raise
        finally:
            duration = time.time() - start_time
            PIPELINE_DURATION_SECONDS.observe(duration)
    return wrapper