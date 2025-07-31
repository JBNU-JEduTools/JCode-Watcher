# Watcher Filemon - 파일 시스템 실시간 감시 서비스

학생 과제 파일의 변경사항을 실시간으로 감지하고 스냅샷을 생성하는 파일 모니터링 서비스입니다.

## 📋 목차

1. [개요](#-개요)
2. [시스템 아키텍처](#-시스템-아키텍처)
3. [설치 및 실행](#-설치-및-실행)
4. [사용 가이드](#-사용-가이드)
5. [모니터링](#-모니터링)
6. [개발자 가이드](#-개발자-가이드)
7. [문제 해결](#-문제-해결)

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
│ │ 학생별 코드          │        │ 파일 변화를          │          │ 코드 변경 이력       │ │
│ │ 파일 저장소          │inoitfy │ 실시간 감지하고      │          │ 스냅샷 저장소        │ │
│ │                     │변화감지 │ 스냅샷 생성          │스냅샷저장 │                    │ │
│ │ class-1-202012345/  │───────►│                     │────────► │ class/hw1/202012345/│ │
│ │ ├── hw1/hello.c     │        │                     │          │ └ hello.c           │ │
│ │ ├── hw2/app.cpp     │        │                     │          │  ├ 20250101_120101.c│ │
│ │ └── hw3/project.py  │        │                     │          │  ├ 20250101_120102.c│ │
│ │                     │        │                     │          │  └ 20250101_120102.c│ │
│ └─────────────────────┘        └───────┬──┬──────────┘          └─────────────────────┘ │
│            ▲      /watcher/codes       │  │                                ▲            │
│            │        (RO Mount)         │  │       /watcher/snapshots       │            │
│            └───────────────────────────┘  └────────────────────────────────┘            │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```


### 실행 순서

### 사전 요구사항
```bash
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

#### 3. Filemon 실행
```bash
cd packages/filemon
docker compose up --build
```

### 서비스 접속
- **Code Server**: https://localhost:8080 (비밀번호: `filemon`)
- **Filemon 메트릭**: http://localhost:9090






## 주요 설정 (`src/config/settings.py`)


#### 감시 대상 파일 패턴
```python
SOURCE_PATTERNS = [
    # 0depth: /watcher/codes/class-1-202012345/hw1/hello.c
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/[^/]+\.(c|h|py|cpp|hpp)$",
    
    # 1depth: /watcher/codes/class-1-202012345/hw1/src/hello.c  
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/[^/]+/[^/]+\.(c|h|py|cpp|hpp)$",
    
    # 2depth: /watcher/codes/class-1-202012345/hw1/src/utils/hello.c
    r"/watcher/codes/[^/]+-[^/]+-[^/]+/hw(?:[0-9]|10)/[^/]+/[^/]+/[^/]+\.(c|h|py|cpp|hpp)$"
]
```

#### 기본 경로 설정
```python
WATCH_PATH = BASE_DIR / "codes"           # /watcher/codes
SNAPSHOT_DIR = BASE_DIR / "snapshots"     # /watcher/snapshots
MAX_FILE_SIZE = 64 * 1024                 # 64KB 제한
```

#### 무시할 파일 패턴
```python
IGNORE_PATTERNS = [
    r".*/(?:\.?env|ENV)/.+",          # 환경 변수 파일
    r".*/(?:site|dist)-packages/.+",   # Python 패키지
    r".*/lib(?:64|s)?/.+",            # 라이브러리 디렉토리
    r".*/\..+",                        # 숨김 파일/디렉토리
]
```

### 파일 감지 규칙
- **학생 식별**: `클래스-분반-학번` 형태 (예: `class-1-202012345`)
- **과제 범위**: `hw1` ~ `hw10`
- **파일 확장자**: `.c`, `.h`, `.py`, `.cpp`, `.hpp`
- **최대 깊이**: 과제 폴더 기준 2depth까지
- **파일 크기**: 64KB 이하만 처리

### 스냅샷 저장 구조
```
/watcher/snapshots/
└── [클래스]/                      # class
    └── [과제]/                    # hw1  
        └── [학번]/                # 202012345
            └── [파일명]/          # hello.c
                └── [타임스탬프].c # 20250101_120101.c
```

## 📊 모니터링

### 실시간 로그 확인
```bash
# Filemon 로그 모니터링
docker compose logs -f watcher-filemon
```

**예상 출력:**
```
watcher-filemon | [2024-01-01 12:00:00] File event: CREATE /watcher/codes/class-1-202012345/hw1/main.py
watcher-filemon | [2024-01-01 12:00:01] File event: MODIFY /watcher/codes/class-1-202012345/hw1/main.py
watcher-filemon | [2024-01-01 12:00:01] Snapshot created: main.py.1704067201.snapshot
```

### 스냅샷 관리
```bash
# 생성된 스냅샷 목록 확인
ls -la snapshots/

# 스냅샷 내용 확인 (클래스/과제/학번 구조로 저장됨)
cat snapshots/class/hw1/202012345/main.py.*.snapshot
```

### 메트릭 확인
- **Prometheus 메트릭**: http://localhost:9090
- **파일 감지 통계**, **API 호출 상태** 등 모니터링 가능

## 🔧 개발자 가이드

### 프로젝트 구조
```
packages/filemon/
├── src/                   # 소스 코드
├── snapshots/            # 스냅샷 저장소 (자동 생성)
├── logs/                 # 로그 파일 (자동 생성)
├── docker-compose.yml    # 서비스 구성
└── Dockerfile           # 컨테이너 이미지
```

### 개발 워크플로우
```bash
# 서비스 시작
docker compose up --build

# 로그 확인
docker compose logs -f watcher-filemon

# 서비스 재시작
docker compose restart watcher-filemon

# 환경 정리
docker compose down
```

### 환경 변수 설정
| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `WATCHER_LOG_LEVEL` | `DEBUG` | 로그 레벨 |
| `WATCHER_API_URL` | `http://172.17.0.1:3000` | 백엔드 API 엔드포인트 |

### 지원 파일 형식 및 구조
- **파일 확장자**: `.c`, `.h`, `.py`, `.cpp`, `.hpp`
- **과제 디렉토리**: `hw1` ~ `hw10` (최대 2depth 서브디렉토리)
- **학생 식별**: `수업명-분반-학번` 형태

## 🚨 문제 해결

### 파일 감지 안됨
```bash
# inotify 제한 증가
echo 'fs.inotify.max_user_watches=524288' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 권한 문제
```bash
chmod -R 755 /home/ubuntu/jcode
```

---

**이제 filemon을 통해 학생들의 과제 파일을 실시간으로 모니터링할 수 있습니다!** 🎉