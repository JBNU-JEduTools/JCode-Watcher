# Ubuntu 베이스 이미지 사용
FROM ubuntu:24.04
COPY --from=ghcr.io/astral-sh/uv:0.8.11 /uv /uvx /bin/

# Python 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-bpfcc \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# 가상 환경 설정
RUN uv venv --system-site-packages /opt/venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# 의존설 설치
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 로그 디렉터리
RUN mkdir -p /app/logs

# 코드 복사
COPY src ./src
COPY run.py ./


CMD ["/opt/venv/bin/python3", "run.py"]
