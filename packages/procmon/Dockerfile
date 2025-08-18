# Ubuntu 베이스 이미지 사용
FROM ubuntu:24.04
COPY --from=ghcr.io/astral-sh/uv:0.8.11 /uv /uvx /bin/

# Python 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-bpfcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN uv venv --system-site-packages /opt/venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv


RUN uv sync --frozen --no-dev

COPY src ./src
CMD ["/opt/venv/bin/python3", "-m", "src.app"]
