# Watcher Procmon - 프로세스 실시간 감시 서비스

eBPF를 활용한 실시간 프로세스 모니터링 시스템입니다. 컨테이너 환경에서의 프로세스 실행을 감지하고, 컴파일러 및 Python 실행을 추적하여 코딩 활동 분석을 수행합니다.

## 📋 목차

1. [개요](#1-개요)
2. [아키텍처](#2-아키텍처)
3. [설치 및 환경 설정](#3-설치-및-환경-설정)
4. [실행 방법](#4-실행-방법)
5. [설정 가이드](#5-설정-가이드)
6. [API 사용법](#6-api-사용법)
7. [모니터링 및 메트릭](#7-모니터링-및-메트릭)
8. [개발 가이드](#8-개발-가이드)
9. [문제 해결](#9-문제-해결)
10. [기여 방법](#10-기여-방법)

## 1. 개요

### 프로젝트 소개
Procmon은 eBPF(Extended Berkeley Packet Filter)를 사용하여 리눅스 시스템에서 프로세스 실행을 실시간으로 모니터링하는 시스템입니다. 특히 교육 환경에서 학생들의 프로그래밍 활동을 추적하고 분석하는 데 최적화되어 있습니다.

### 주요 기능
- **코딩 활동 분석**: eBPF를 통한 실시간 프로세스 모니터링
  - 컴파일러 감지 및 분석 (GCC, Clang, G++ 등)
  - 빌드된 프로세스 실행 추적 (C/C++ 실행 파일, Python 스크립트)
  - 개발 워크플로우 패턴 분석

### 시스템 요구사항
- Ubuntu 24.04
- Linux 커널 6.8.0-55-generic
- Python 3.7+
- 관리자 권한 (CAP_SYS_ADMIN, CAP_SYS_PTRACE)

## 2. 아키텍처

### 전체 시스템 구조
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BPF Program   │───▶│  Event Queue   │───▶│ Handler Chain   │
│   (program.c)   │    │  (AsyncIO)      │    │  (Processing)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Kernel Events   │    │ Event Builder   │    │   API Client    │
│   (exec, etc)   │    │   (Models)      │    │ (HTTP Sender)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 3. 설치 및 환경 설정

### 시스템 요구사항
```bash
# eBPF 개발 도구 설치 (Ubuntu/Debian)
sudo apt-get install -y \
    linux-headers-$(uname -r) \
    libbpf-dev \
```

### Python 환경 설정
```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### Docker 환경 설정
```bash
# 이미지 빌드
docker build -t procmon:latest .

# Docker Compose 사용
docker-compose up -d
```

## 4. 실행 방법

### 로컬 실행
```bash
# 기본 실행
sudo python3 -m src.app

# 환경 변수와 함께 실행
LOG_LEVEL=DEBUG API_ENDPOINT=http://api.example.com sudo python3 -m src.app
```

### Docker 컨테이너 실행

#### 권장 실행 명령어 (최소 권한)
```bash
docker run -it \
  --cap-drop=ALL \
  --cap-add=SYS_ADMIN \
  --cap-add=SYS_PTRACE \
  --pid=host \
  -v /sys/kernel/debug:/sys/kernel/debug:ro \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  procmon:latest
```

#### 개발용 실행 (전체 권한)
```bash
docker run -it \
  --privileged \
  --pid=host \
  -v /sys/kernel/debug:/sys/kernel/debug \
  -v /lib/modules:/lib/modules:ro \
  -v /usr/src:/usr/src:ro \
  procmon:latest
```

### 권한 설정
- **CAP_SYS_ADMIN**: eBPF 프로그램 로딩에 필요
- **CAP_SYS_PTRACE**: 프로세스 정보 접근에 필요
- **--pid=host**: 호스트 프로세스 모니터링에 필요

## 5. 설정 가이드


### 주요 컴포넌트

#### BPF 모듈 (`bpf/`)
- **collector.py**: eBPF 프로그램 로딩 및 이벤트 수집
- **event.py**: BPF 이벤트 데이터 모델
- **program.c**: 커널 공간에서 실행되는 eBPF 프로그램

#### 이벤트 핸들러 (`handlers/`)
- **chain.py**: 핸들러 체인 구성 및 실행
- **process.py**: 프로세스 정보 처리
- **enrichment.py**: 이벤트 데이터 보강
- **homework.py**: 코딩 활동 분석 로직
- **api.py**: 외부 API 연동

#### 파서 시스템 (`parser/`)
- **compiler.py**: 컴파일러 명령어 파싱
- **cpp_compiler.py**: C/C++ 컴파일러 전용 파서
- **python.py**: Python 실행 파서

#### 프로세스 필터링 (`process/`)
- **filter.py**: 프로세스 타입 판별 및 필터링
- **types.py**: 프로세스 타입 정의

#### 과제 요구사항 검증 (`homework/`)
- **checker.py**: 과제 조건 매칭 및 프로세스 검증


### 환경 변수 설정
```bash
# API 설정
export API_ENDPOINT="http://localhost:8000"
export API_TIMEOUT="20"

# 로깅 설정
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

# 프로메테우스 설정
export PROMETHEUS_PORT="9090"
```

### 프로세스 패턴 구성
`src/config/settings.py`에서 모니터링할 프로세스 패턴을 설정할 수 있습니다:

```python
PROCESS_PATTERNS = {
    "GCC": ["/usr/bin/x86_64-linux-gnu-gcc-13"],
    "PYTHON": ["/usr/bin/python3.11", "/usr/bin/python3.10"],
    # 추가 패턴...
}
```

## 6. API 사용법

### REST API 엔드포인트
시스템은 내부적으로 HTTP API를 사용하여 이벤트를 전송합니다.

#### 클라이언트 사용 예제
```python
from src.api.client import APIClient

# 클라이언트 초기화
client = APIClient("http://localhost:8000")

# 이벤트 전송
await client.send_event({
    "process_type": "PYTHON",
    "binary_path": "/usr/bin/python3",
    "arguments": ["script.py"],
    "timestamp": "2024-01-01T00:00:00Z"
})
```

### 응답 형식
```json
{
    "status": "success",
    "message": "Event processed successfully",
    "event_id": "uuid-here"
}
```

## 7. 모니터링 및 메트릭

### Prometheus 메트릭
시스템은 다음과 같은 메트릭을 제공합니다:

- `procmon_events_total`: 총 이벤트 수
- `procmon_events_by_type`: 타입별 이벤트 수
- `procmon_processing_duration_seconds`: 처리 시간
- `procmon_errors_total`: 오류 수

### 메트릭 수집 설정
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'procmon'
    static_configs:
      - targets: ['localhost:9090']
```

### 로그 구조
```json
{
    "timestamp": "2024-01-01T00:00:00Z",
    "level": "INFO",
    "message": "[이벤트 처리 완료] 타입: PYTHON",
    "pid": 1234,
    "hostname": "container-abc123"
}
```

## 8. 개발 가이드

### 프로젝트 구조 상세
```
src/
├── app.py              # 메인 애플리케이션
├── api/                # API 클라이언트
├── bpf/                # eBPF 관련 모듈
├── config/             # 설정 관리
├── events/             # 이벤트 모델
├── handlers/           # 이벤트 처리 핸들러
├── homework/           # 코딩 활동 분석 로직
├── metrics/            # 메트릭 수집
├── parser/             # 명령어 파서
├── process/            # 프로세스 필터링
└── utils/              # 유틸리티
```

### 새로운 핸들러 추가
```python
from src.handlers.base import BaseHandler

class CustomHandler(BaseHandler):
    async def handle(self, builder):
        # 커스텀 로직 구현
        return await self.next_handler.handle(builder)
```

### 새로운 파서 구현
```python
from src.parser.base import BaseParser

class CustomParser(BaseParser):
    def parse(self, binary_path, arguments):
        # 파싱 로직 구현
        return parsed_data
```

### 테스트 실행
```bash
# 전체 테스트
pytest

# 특정 모듈 테스트
pytest tests/parser/

# 커버리지와 함께
pytest --cov=src
```

## 9. 문제 해결

### 일반적인 오류

#### eBPF 프로그램 로딩 실패
```bash
# 커널 헤더 확인
ls /lib/modules/$(uname -r)/build

# eBPF 지원 확인
zcat /proc/config.gz | grep BPF
```

#### 권한 관련 문제
```bash
# 필요한 권한 확인
sudo setcap cap_sys_admin,cap_sys_ptrace+ep /usr/bin/python3

# 또는 sudo로 실행
sudo python3 -m src.app
```

### BPF 관련 문제
- **컴파일 오류**: 커널 헤더와 clang 버전 확인
- **로딩 실패**: 커널 버전 및 eBPF 지원 확인
- **권한 거부**: CAP_SYS_ADMIN 권한 확인

### 컨테이너 해시 관련
컨테이너 식별을 위한 cgroup 정보:
- Docker: `docker-9a879f2ecd371ce4724...`
- Kubernetes: `cri-containerd-6cc798ea...`

### 디버깅 도구
```bash
# BPF 트레이스 확인
sudo cat /sys/kernel/debug/tracing/trace_pipe

# 이벤트 로그 확인
sudo journalctl -f -u procmon
```

## 10. 기여 방법

### 개발 환경 구성
```bash
# 저장소 클론
git clone <repository-url>
cd procmon

# 개발 의존성 설치
pip install -r requirements-dev.txt

# 프리커밋 훅 설치
pre-commit install
```

### 코드 스타일
- **포매터**: Black
- **린터**: Flake8, Pylint
- **타입 힌트**: MyPy 사용 권장
- **독스트링**: Google 스타일

### 테스트 작성
```python
import pytest
from src.parser.python import PythonParser

class TestPythonParser:
    def test_parse_simple_script(self):
        parser = PythonParser()
        result = parser.parse("/usr/bin/python3", ["script.py"])
        assert result.source_file == "script.py"
```

### 풀 리퀘스트 가이드라인
1. 기능별로 브랜치 생성
2. 적절한 테스트 코드 작성
3. 문서 업데이트
4. CI/CD 파이프라인 통과 확인

---

## 라이선스
MIT License

## 연락처
- 이슈 리포트: GitHub Issues
- 문의사항: 프로젝트 관리자에게 연락

