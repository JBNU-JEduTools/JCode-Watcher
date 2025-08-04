# Watcher Filemon - 파일 시스템 실시간 감시 서비스

학생 과제 파일의 변경사항을 실시간으로 감지하고 스냅샷을 생성하는 파일 모니터링 서비스입니다.

## 📋 목차

1. [개요](#-개요)
2. [시스템 아키텍처](#-시스템-아키텍처)
3. [설치 및 실행](#-설치-및-실행)
4. [사용 가이드](#-사용-가이드)
5. [모니터링](#-모니터링)
6. [백엔드 연동](#-백엔드-연동)
7. [개발자 가이드](#-개발자-가이드)
8. [테스트](#-테스트)
9. [문제 해결](#-문제-해결)

## 📋 개요

### 주요 기능
- **실시간 파일 감시**: inotify를 사용한 파일 변경 즉시 감지
- **자동 스냅샷 생성**: 파일 변경 시점의 내용을 타임스탬프와 함께 보관
- **이벤트 전송**: 백엔드 API로 파일 변경 이벤트 실시간 전송
- **메트릭 제공**: Prometheus 형식의 모니터링 지표 (포트 9090)


## 🏗️ 시스템 아키텍처

### 시스템 구조 다이어그램

```
          ┌─────────┐
          │ Student │
          │         │
          └─────────┘
               │
        코드 작성 및 편집
             (HTTP)
               │
┌──────────────┼──────────────────────────────────────────────────────────────────────────┐
│              ▼                                                             Host System  │
│   ┌──────────────────────┐                                                              │
│   │ Code-server          │                                                              │
│   │ Container:8443       │                                                              │
│   │ 웹 기반 코드          │                                                              │
│   │ 편집 환경             │                                                              │
│   └──────────┬───────────┘                                                              │
│              │                                                                          │
│       파일 읽기/쓰기                                                                     │
│   /config/workspace (RW Mount)                                                          │
│              │                                                                          │
│              ▼                                                                          │
│ ┌─────────────────────┐        ┌─────────────────────┐          ┌─────────────────────┐ │
│ │ Workspace Volume    │        │ Filemon Container   │          │ Snapshot Volume     │ │
│ │                     │        │                     │          │                     │ │
│ │ 학생별 코드          │        │ 파일 변화를           │          │ 코드 변경 이력        │ │
│ │ 파일 저장소          │inoitfy │ 실시간 감지하고        │ 스냅샷저장 │                     │ │
│ │                     │변화감지 │ 스냅샷 생성           │────────► │ class/hw1/202012345/│ │
│ │ class-1-202012345/  │───────►│                     │          │ └ hello.c           │ │
│ │ ├── hw1/hello.c     │        │                     │          │  ├ 20250101_120101.c│ │
│ │ ├── hw2/app.cpp     │        │                     │          │  ├ 20250101_120102.c│ │
│ │ └── hw3/project.py  │        │                     │          │  └ 20250101_120102.c│ │
│ └─────────────────────┘        └───────┬──┬──────────┘          └─────────────────────┘ │
│            ▲      /watcher/codes       │  │                                ▲            │
│            │        (RO Mount)         │  │       /watcher/snapshots       │            │
│            └───────────────────────────┘  └────────────────────────────────┘            │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 설치 및 실행

### 사전 요구사항
```bash
# Ubuntu 24.04
# Docker 설치
docker --version
```

#### 1. 학생 작업 디렉토리 생성
```bash
mkdir -p /home/ubuntu/jcode/class-1-202012345
```

#### 2. Code Server 실행
```bash
sudo docker run -d \
        --name jcode-class-1-202012345 \
        -p 8080:8443 \
        -e PASSWORD="filemon" \
        -v /home/ubuntu/jcode/class-1-202012345/:/config/workspace\
        --hostname jcode-class-1-202012345 \
        lscr.io/linuxserver/code-server:latest
```

### 3. Filemon 실행 및 확인

#### 1. Filemon 실행
아래 명령어로 `filemon` 서비스를 빌드하고 실행합니다.

```bash
cd packages/filemon
docker compose up --build
```

#### 2. 과제 파일 생성 및 변경
Code Server (`https://localhost:8080`, PW: `filemon`)에 접속하여 과제 파일을 생성하거나 수정합니다.

> 과제 파일은 반드시 `hw`로 시작하는 과제 디렉토리 내에 생성해야 합니다. (예: `hw1`, `hw2`)

```bash
# 예시: hw1 과제 디렉토리 및 C 소스 파일 생성
mkdir -p /config/workspace/hw1
echo '#include <stdio.h>\nint main() { printf("Hello, World!\n"); return 0; }' > /config/workspace/hw1/hello.c
```

#### 3. 변경 감지 및 스냅샷 확인
`filemon`은 파일 변경을 감지하여 로그를 남기고 스냅샷을 생성합니다.

**실시간 로그 확인**

```bash
docker compose logs -f watcher-filemon
```

**주요 로그:**
```
watcher-filemon-1 | INFO - 이벤트 감지됨 - 타입: modified, 경로: /watcher/codes/class-1-202012345/hw1/hello.c
watcher-filemon-1 | INFO - 스냅샷 생성 완료 - 경로: /watcher/snapshots/class-1/hw1/202012345/hello.c/20250731_083420.c
watcher-filemon-1 | ERROR - API 오류 발생 - ...
```

**스냅샷 생성 확인**

```bash
# 생성된 스냅샷 확인 (타임스탬프 형태의 파일)
ls -la snapshots/class-1/hw1/202012345/hello.c
```

위 과정을 통해 `filemon`이 정상적으로 동작하는 것을 확인할 수 있습니다.

## 📊 모니터링

### Prometheus 메트릭 서버

`filemon`은 포트 9090에서 Prometheus 형식의 메트릭을 제공합니다.

#### 메트릭 확인
```bash
# 메트릭 엔드포인트 접속
curl http://localhost:9090/metrics

# 또는 브라우저에서
http://localhost:9090/metrics
```

#### 현재 제공되는 메트릭

현재는 **Python 런타임 기본 메트릭**만 제공됩니다:

| 메트릭 카테고리 | 메트릭명 | 설명 |
|---|---|---|
| **Python GC** | `python_gc_objects_collected_total` | 가비지 컬렉션으로 수집된 객체 수 |
| | `python_gc_collections_total` | 가비지 컬렉션 실행 횟수 |
| **프로세스** | `process_resident_memory_bytes` | 실제 사용 중인 메모리 크기 |
| | `process_virtual_memory_bytes` | 가상 메모리 크기 |
| | `process_cpu_seconds_total` | 총 CPU 사용시간 |
| | `process_open_fds` | 열린 파일 디스크립터 수 |
| **Python 정보** | `python_info` | Python 버전 및 구현체 정보 |

#### 추가 예정 메트릭

향후 filemon 애플리케이션 고유 메트릭이 추가될 예정입니다:

- `watcher_events_processed_total`: 처리된 파일 이벤트 수
- `watcher_snapshots_created_total`: 생성된 스냅샷 수
- `watcher_api_calls_total`: 백엔드 API 호출 횟수
- `watcher_event_queue_size`: 이벤트 큐 대기 작업 수
- `watcher_processing_duration_seconds`: 이벤트 처리 시간


## 👨‍💻 개발자 가이드 (Developer Guide)

### 개발 환경 정책

**`filemon`의 개발은 Docker 컨테이너 환경에서만 진행하는 것을 원칙으로 합니다.**

로컬 머신에 직접 Python 개발 환경을 구성하는 방식 대신 모든 개발 과정은 아래에 설명된 Docker 기반 환경을 통해 이루어져야 합니다.

### 실시간 코드 수정 및 디버깅

소스 코드는 Docker 볼륨을 통해 컨테이너와 실시간으로 동기화됩니다. 로컬에서 코드를 수정하면 즉시 실행 중인 컨테이너에 반영됩니다. 재시작 하기 위해서는 컨테이너를 내렸다가 다시 띄워야 합니다.

### 아키텍처 및 상세 동작 흐름

Filemon은 이벤트 기반으로 동작하며, 각 모듈은 명확한 단일 책임을 갖습니다. 새로운 기능을 추가하거나 문제를 해결해야 할 때, 아래 설명을 참고하여 어떤 코드를 수정해야 할지 파악할 수 있습니다.

### 핵심 모듈의 역할과 책임

| 모듈 파일명 | 역할과 책임 |
| :--- | :--- |
| `app.py` | **애플리케이션 진입점.** 설정 로딩, 로거 초기화 후 `watchdog` 옵저버를 생성하고 실행하여 파일 시스템 감시를 시작합니다. |
| `core/watchdog_handler.py` | **파일 시스템 이벤트의 최초 수신자.** `watchdog` 라이브러리로부터 직접 이벤트를 받아, 후속 처리를 위해 내부 큐(Queue)에 이벤트 정보(`event_type`, `src_path`)를 전달합니다. |
| `core/event_processor.py` | **이벤트 처리의 핵심 두뇌.** 큐에서 이벤트를 가져와 처리할지 여부를 결정합니다. `settings.py`의 규칙(소스 패턴, 무시 패턴, 파일 크기)에 따라 유효성을 검사하고, 통과 시 다른 모듈을 호출하여 실제 동작을 위임합니다. |
| `core/path_info.py` | **경로 분석 전문가.** 이벤트가 발생한 파일의 절대 경로(e.g., `/watcher/codes/class-1-202012345/hw1/hello.c`)를 분석하여, 스냅샷 저장 및 API 전송에 필요한 구조적인 정보(클래스, 과제, 학번, 파일명 등)를 추출합니다. |
| `core/snapshot.py` | **스냅샷 생성 및 관리자.** `event_processor`의 요청을 받아 스냅샷을 생성합니다. 단, 직전 스냅샷과 현재 파일 내용를 비교하여 변경된 경우에만 새로운 타임스탬프 스냅샷을 저장함으로써 중복을 방지합니다. |
| `core/api.py` | **외부 API 연동 채널.** 스냅샷 생성과 같은 주요 이벤트 발생 시, `settings.py`에 정의된 백엔드 API 서버로 관련 정보를 HTTP POST로 전송합니다. |
| `metrics/prometheus.py` | **시스템 계측기.** 파일 이벤트 발생, 스냅샷 생성, API 호출 성공/실패 등 시스템의 주요 동작을 카운트하여 Prometheus가 수집할 수 있는 메트릭(`:9090/metrics`)을 노출합니다. |
| `config/settings.py` | **중앙 설정 저장소.** 감시할 경로, 파일 패턴, API 주소, 로그 레벨 등 시스템의 모든 주요 설정을 변수로 관리합니다. |

### 파일 변경 이벤트의 전체 라이프사이클

학생이 코드를 저장했을 때부터 스냅샷이 생성되기까지, 데이터는 아래와 같은 순서로 각 모듈을 거치며 처리됩니다.

1.  **[사용자]** 학생이 Code-Server에서 `.../hw1/hello.c` 파일을 저장합니다.
2.  **[watchdog_handler.py]** `on_modified` 이벤트를 수신하고, 이벤트 정보를 내부 큐에 넣습니다.
3.  **[event_processor.py]** 큐에서 `hello.c` 수정 이벤트를 꺼내 유효성 검사를 시작합니다.
    - `settings.py`의 `SOURCE_PATTERNS` 정규식과 일치하는가? -> **(통과)**
    - `IGNORE_PATTERNS`에 해당하지 않는가? -> **(통과)**
    - `MAX_FILE_SIZE`를 초과하지 않는가? -> **(통과)**
4.  **[event_processor.py]** 유효한 이벤트이므로, `path_info.py`를 호출하여 경로 분석을 요청합니다.
5.  **[path_info.py]** `/watcher/codes/class-1-202012345/hw1/hello.c` 경로를 분석하여 `class='class-1'`, `hw='hw1'`, `student_id='202012345'` 등의 정보를 담은 객체를 반환합니다.
6.  **[event_processor.py]** 분석된 경로 정보를 바탕으로 `snapshot.py`에 스냅샷 생성을 요청합니다.
7.  **[snapshot.py]** 최신 스냅샷과 현재 파일 내용을 비교합니다. 내용이 다르다고 판단되면, 타임스탬프가 포함된 새 스냅샷 파일(e.g., `.../20250731_103000.c`)을 생성합니다.
8.  **[event_processor.py]** 스냅샷 생성이 성공적으로 완료되면, `api.py`를 호출하여 백엔드 서버에 알림을 전송합니다.
9.  **[prometheus.py]** `events_processed_total`, `snapshots_created_total` 등 관련된 모든 메트릭의 카운터를 1씩 증가시킵니다.



## 주요 설정 (`src/config/settings.py`)

### 환경 변수 설정
| 변수명 | 기본값 | 설명 |
|---|---|---|
| `WATCHER_LOG_LEVEL` | `INFO` | 로그 레벨 (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `WATCHER_API_URL` | `http://172.17.0.1:3000` | 백엔드 API 엔드포인트 |
| `LOG_DIR` | `/app/logs` | 로그 파일이 저장될 디렉토리 |
| `LOG_MAX_BYTES` | `52428800` (50MB) | 로그 파일의 최대 크기 (단위: bytes) |
| `LOG_BACKUP_COUNT` | `0` | 보관할 백업 로그 파일의 최대 개수 |

### 지원 파일 형식 및 구조
- **파일 확장자**: `.c`, `.h`, `.py`, `.cpp`, `.hpp`
- **과제 디렉토리**: `hw1` ~ `hw10` (최대 2depth 서브디렉토리)
- **학생 식별**: `수업명-분반-학번` 형태



#### 기본 경로 설정
```python
WATCH_PATH = BASE_DIR / "codes"           # /watcher/codes
SNAPSHOT_DIR = BASE_DIR / "snapshots"     # /watcher/snapshots
MAX_FILE_SIZE = 64 * 1024                 # 감시대상(watcher/codes)의 크기 64KB 제한
```

#### 감시 대상 파일 패턴
```python
# 과제 폴더 기준 2depth까지
# 클래스-분반-학번 형태 (예: class-1-202012345)
# 과제 범위: hw1 ~ hw10
# 파일 확장자: .c, .h, .py, .cpp, .hpp
SOURCE_PATTERNS = [
    # 0depth: /watcher/codes/class-1-202012345/hw1/hello.c
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/[^/]+\.(c|h|py|cpp|hpp)$",
    
    # 1depth: /watcher/codes/class-1-202012345/hw1/src/hello.c  
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/[^/]+/[^/]+\.(c|h|py|cpp|hpp)$",
    
    # 2depth: /watcher/codes/class-1-202012345/hw1/src/utils/hello.c
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/[^/]+/[^/]+/[^/]+\.(c|h|py|cpp|hpp)$"
]

# 무시할 파일 패턴
IGNORE_PATTERNS = [
    r".*/(?:\.?env|ENV)/.+",          # 환경 변수 파일
    r".*/(?:site|dist)-packages/.+",   # Python 패키지
    r".*/lib(?:64|s)?/.+",            # 라이브러리 디렉토리
    r".*/\\..+",                        # 숨김 파일/디렉토리
]
```

### 스냅샷 저장 구조
```
/watcher/snapshots/
└── [클래스]/                      # class
    └── [과제]/                    # hw1  
        └── [학번]/                # 202012345
            └── [파일명]/          # hello.c
                └── [타임스탬프].c # 20250101_120101.c
```


## 🔗 백엔드 연동

`filemon`은 감지한 파일 변경 정보를 백엔드 서버로 전송합니다. 백엔드 서버는 학생들의 코드 제출 이력을 저장하고 분석하는 역할을 합니다.

### 백엔드 실행

`filemon`과 연동하기 위해 아래 명령어로 백엔드 서비스를 실행할 수 있습니다.

```bash
# 프로젝트 루트 디렉토리에서 실행
cd packages/backend
docker compose up --build -d
```

### IP 주소 확인

`filemon` 컨테이너가 백엔드 컨테이너와 통신하려면 정확한 IP 주소 설정이 필요합니다.

- **기본 설정**: `filemon`은 기본적으로 백엔드 API 서버 주소를 `http://172.17.0.1:3000`으로 가정합니다. 이 IP는 Docker의 기본 브리지 네트워크 게이트웨이 주소입니다.
- **설정 변경**: 만약 사용자의 Docker 네트워크 환경이 다르거나 백엔드 서버가 다른 호스트에서 실행되는 경우, IP 주소를 직접 수정해야 합니다. `docker-compose.yml` 파일에 `WATCHER_API_URL` 환경 변수를 설정하여 API 주소를 변경할 수 있습니다.

## 🧪 테스트

### 테스트 실행

```bash
# 모든 테스트 실행
docker compose run --rm watcher-filemon python -m pytest

# 특정 테스트 파일 실행
docker compose run --rm watcher-filemon python -m pytest tests/test_path_info.py

# 커버리지 포함 실행
docker compose run --rm watcher-filemon python -m pytest --cov=src --cov-report=html

# 상세 출력으로 실행
docker compose run --rm watcher-filemon python -m pytest -v
```

### 테스트 구조

```
tests/
├── test_path_info.py         # 경로 분석 로직
├── test_snapshot.py          # 스냅샷 생성/관리
├── test_api.py              # 백엔드 API 연동
├── test_event_processor.py  # 이벤트 처리
└── test_watchdog_handler.py # 파일 감시 핸들러
```

### 테스트 환경

- **프레임워크**: pytest + pytest-asyncio
- **모킹**: aioresponses (HTTP API 모킹)
- **임시 파일**: pytest의 tmp_path fixture 활용
- **실행 환경**: Docker 컨테이너 내에서만 실행

### 새 테스트 작성 시 참고사항

- 비동기 함수는 `@pytest.mark.asyncio` 데코레이터 사용
- 파일 시스템 테스트는 `tmp_path` fixture 활용
- API 테스트는 `aioresponses`로 HTTP 호출 모킹
- 테스트 함수명: `test_[기능]_[상황]` 형태로 명명

## 🛠️ 문제 해결

### 일반적인 문제 및 해결 방법

#### 1. 컨테이너 실행 실패

**문제**: `docker compose up` 실행 시 컨테이너가 시작되지 않음

**해결 방법**:
```bash
# 상세 로그 확인
docker compose logs -f watcher-filemon

# 컨테이너 상태 확인
docker compose ps

# 강제 재빌드
docker compose up --build --force-recreate
```

**일반적인 원인**:
- 포트 9090이 이미 사용 중
- 볼륨 마운트 경로 문제
- Docker 이미지 빌드 실패

#### 2. 파일 변경이 감지되지 않음

**문제**: 코드를 수정해도 filemon이 반응하지 않음

**진단 방법**:
```bash
# 실시간 로그 확인
docker compose logs -f watcher-filemon

# 감시 중인 경로 확인
ls -la /home/ubuntu/jcode/class-1-202012345/
```

**해결 방법**:
- 파일이 `hw1` ~ `hw10` 디렉토리 내에 있는지 확인
- 지원 확장자 `.c`, `.h`, `.py`, `.cpp`, `.hpp` 사용 확인
- 파일 크기가 64KB 이하인지 확인
- 파일명에 특수문자나 한글이 없는지 확인

#### 3. 스냅샷이 생성되지 않음

**문제**: 파일 변경은 감지되지만 스냅샷 폴더에 파일이 없음

**확인 사항**:
```bash
# 스냅샷 디렉토리 확인
ls -la snapshots/

# 권한 문제 확인
docker compose exec watcher-filemon ls -la /watcher/snapshots
```

**해결 방법**:
- 스냅샷 디렉토리 권한 확인 (`chmod 755 snapshots/`)
- 디스크 용량 확인
- 동일한 내용의 파일은 중복 스냅샷을 생성하지 않음 (정상 동작)

#### 4. 백엔드 API 연결 실패

**문제**: 로그에 API 오류 메시지가 계속 출력됨

**로그 예시**:
```
ERROR - API 오류 발생 - 백엔드 서버 응답 실패
```

**해결 방법**:
```bash
# 백엔드 서버 상태 확인
curl http://172.17.0.1:3000/health

# Docker 네트워크 IP 확인
docker network inspect bridge | grep Gateway

# API URL 환경변수 변경
# docker-compose.yml에서 WATCHER_API_URL 수정
```

#### 5. 메트릭이 보이지 않음

**문제**: `http://localhost:9090/metrics` 접속 시 연결 거부

**해결 방법**:
```bash
# 포트 바인딩 확인
docker compose ps

# 컨테이너 내부에서 메트릭 서버 확인
docker compose exec watcher-filemon curl localhost:9090/metrics

# 방화벽 설정 확인 (Windows/Linux)
```

#### 6. 로그 확인 및 디버깅

**실시간 로그 모니터링**:
```bash
# 전체 로그
docker compose logs -f

# 에러 로그만 필터링
docker compose logs -f | grep ERROR

# 특정 시간 이후 로그
docker compose logs --since="2024-01-01T10:00:00"
```

**로그 레벨 변경**:
```yaml
# docker-compose.yml
environment:
  - WATCHER_LOG_LEVEL=DEBUG  # INFO -> DEBUG로 변경
```

#### 7. 권한 문제

**문제**: 파일 접근 권한 관련 오류

**해결 방법**:
```bash
# 워크스페이스 권한 확인
sudo chown -R $USER:$USER /home/ubuntu/jcode/

# 스냅샷 디렉토리 권한 설정
sudo chmod 755 snapshots/
sudo chown -R $USER:$USER snapshots/
```

### 자주 묻는 질문 (FAQ)

**Q: 여러 학생이 동시에 사용할 수 있나요?**
A: 네, `class-분반-학번` 형태로 구분하여 여러 학생의 파일을 동시에 감시할 수 있습니다.

**Q: 스냅샷 저장 용량 제한이 있나요?**
A: 별도 제한은 없지만, 호스트 시스템의 디스크 용량에 따라 제한됩니다.

**Q: 백엔드 없이도 사용할 수 있나요?**
A: 네, 백엔드 API 연결이 실패해도 로컬 스냅샷 생성은 정상적으로 동작합니다. filemon자체의 개발은 backend 연동없이도 수행 가능합니다.

