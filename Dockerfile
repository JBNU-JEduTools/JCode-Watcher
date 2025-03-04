# Ubuntu 베이스 이미지 사용
FROM ubuntu:24.04

# Python 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    bpfcc-tools \
    python3-bpfcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src ./src

ENTRYPOINT ["python3"]
CMD ["-m", "src.app"]
