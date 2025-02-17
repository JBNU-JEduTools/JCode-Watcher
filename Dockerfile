# 베이스 이미지 설정
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt .
COPY watcher.py .

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt


# 컨테이너 실행 시 실행할 명령어
CMD ["python", "watcher.py"]
