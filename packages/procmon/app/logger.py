import logging
import sys
from .settings import settings

# 1. "jcode_watcher" 로거 생성
logger = logging.getLogger("jcode_watcher")

# 2. 로그 레벨 설정
logger.setLevel(settings.LOG_LEVEL)

# 3. 로그 포매터 정의
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

# 4. 핸들러 생성 및 포매터 적용
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

# 5. 로거에 핸들러 추가
# 핸들러가 중복 추가되는 것을 방지하기 위해, 로거에 핸들러가 없는 경우에만 추가
if not logger.handlers:
    logger.addHandler(handler)

