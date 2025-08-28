# 베이스 이미지 설정
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# 작업 디렉토리 설정
WORKDIR /opt/filemon

# pyproject.toml과 uv.lock 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치
RUN uv sync --no-dev --frozen

# 애플리케이션 코드 복사
COPY ./app ./app


ENV PATH="/opt/filemon/.venv/bin:$PATH"
CMD ["python", "-m", "app"]