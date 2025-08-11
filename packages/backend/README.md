# JCode Watcher Backend : 프로그래밍 활동 저장 및 분석

**Watcher Backend**는 학생들의 코딩 과제 수행 과정을 실시간으로 저장, 분석하는 FastAPI 기반의 백엔드 시스템입니다.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/doc/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/ko/docs/home/)

> **현재 SQLite 데이터베이스를 기본으로 구축되어 있으며**, 별도 설정 없이 바로 실행 가능합니다.

```
                        ┌──────────────────┐
Collector ──(POST)────► │                  │
                        │  Backend Engine  │
User     ───(GET)─────► │                  │
                        └───────┬──────────┘
                                │
                                ▼
                            [ Database ]
                                │
                                ├─ Stores snapshots, buildLog, runLog
                                │
                                └─ Mount Persistent Volume
```

## 주요 기능

- **코드 스냅샷 추적**: 학생들의 코드 변경 사항을 실시간으로 기록
- **학습 분석**: 학생별/과제별 코딩 패턴 및 통계 분석
- **로그 모니터링**: 빌드 및 실행 로그 추적
- **메트릭 수집**: Prometheus를 통한 시스템 모니터링
- **API문서** : /docs (스웨거 문서 자동 작성)

## 파일 구조

```
/
├── crud/                 # CRUD 작업 정의(DB 처리 로직)
├── data/                 # 데이터 파일 저장소
│   └── example.db
├── db/                   # DB 연결 및 세션 관리
│   └── connection.py
├── dev/                  # Kubernetes 테스트용 yaml 파일(미완)
├── models/               # SQLAlchemy 모델 테이블 정의
├── routers/              # API 라우터 디렉토리
├── schemas/              # Pydantic 스키마 정의(API 요청/응답 구조)
├── services/             # 비즈니스 로직 정의
├── utils/                
│   └── cache.py          # 캐시 처리 로직
├── .env
├── main.py               # FastAPI 애플리케이션 메인 진입점
└── middleware.py         
```

### 주요 기능별 모듈 구성

프로젝트는 **6개의 핵심 기능**으로 구성되어 있으며, 각 기능은 역할별 디렉토리에 동일한 파일명으로 구현되어 있습니다:

| 기능 모듈 | 설명 | 구현 위치 |
|----------|------|-----------|
| **assignment.py** | 과제 기준 스냅샷 처리 | `crud/`, `routers/`, `schemas/`, `services/` |
| **log.py** | 빌드/실행 로그 처리 | `crud/`, `routers/`, `schemas/`, `models/` |
| **metric.py** | Prometheus 메트릭 수집 | `routers/` |
| **selection.py** | 스냅샷 파일 리스트 조회 | `crud/`, `routers/`, `schemas/`, `services/` |
| **snapshot.py** | 코드 스냅샷 관리 | `crud/`, `routers/`, `schemas/`, `models/` |
| **student.py** | 학생 개인 스냅샷 분석 | `crud/`, `routers/`, `schemas/`, `services/` |

**일관된 구조**: 각 기능은 동일한 파일명으로 각 계층에 구현되어 있어 코드를 찾기 쉽고 유지보수가 용이합니다.


## 시작하기

### 전제조건

시작하기 전에 다음 소프트웨어가 설치되어 있는지 확인하세요:

- **Python 3.8+** (Python 3.9 이상 권장)
- **pip** (Python 패키지 관리자)
- **Git** (버전 관리)

**선택사항:**
- **Docker** (컨테이너 환경에서 실행시)
- **Kubernetes** (클러스터 배포시)

### 1. 설치

1-1. **가상환경 생성 (권장)**
```bash
# Python 가상환경 생성
python3 -m venv [가상환경_이름]

# 가상환경 활성화
# Windows
[가상환경_이름]\Scripts\activate
# macOS/Linux
source [가상환경_이름]/bin/activate
```

1-2. **의존성 설치**
```bash
pip install -r requirements.txt
```

### 2. 환경설정

#### 2-1. 환경변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하세요:

```bash
# .env.example 파일을 복사하여 .env 파일 생성
cp .env.example .env

# 또는 직접 생성
touch .env
```

`.env.example` 파일을 참고하여 필요한 환경변수를 설정하세요.

#### 2-2. 데이터베이스 초기화

```bash
# 현재 SQLite 데이터베이스를 기본으로 구축되어 있습니다

# 데이터 디렉토리 생성 (필요시)
mkdir -p data

# 애플리케이션 첫 실행 시 자동으로 데이터베이스 테이블이 생성됩니다
# 위치: data/
```

#### 2-3. 환경 확인

설정이 올바른지 확인하기 위해 다음 명령어로 테스트할 수 있습니다:

```bash
# Python에서 환경변수 로드 테스트
python -c "from schemas.config import settings; print(f'DB URL: {settings.DB_URL}')"
```

## 로컬 실행

```bash
# 개발 모드 (자동 재시작)
uvicorn main:app --reload --port [port번호] --host 0.0.0.0

# 프로덕션 모드
uvicorn main:app --port [port번호] --host 0.0.0.0

# 백그라운드 실행
nohup uvicorn main:app --port [port번호] --host 0.0.0.0 > app.log 2>&1 &
```

### API 엔드포인트

서버가 실행되면 다음 URL에서 API 문서를 확인할 수 있습니다:

**API 문서 확인 (Swagger UI)**
- **/docs** 엔드포인트로 확인

#### 주요 분석 API 엔드포인트

| 카테고리 | 메서드 | 엔드포인트 | 설명 |
|---------|--------|------------|------|
| **학생별 통계 분석** | GET | `/api/graph_data/{class_div}/{hw_name}/{student_id}/{interval}` | 학생별 스냅샷 그래프 데이터 |
| **과제 통계 분석** | GET | `/api/total_graph_data/{class_div}/{hw_name}/{start}/{end}` | 과제별 스냅샷 그래프 데이터 |
| **빌드 로그** | GET | `/api/{class_div}/{hw_name}/{student_id}/logs/build` | 빌드 로그 조회 |
| **실행 로그** | GET | `/api/{class_div}/{hw_name}/{student_id}/logs/run` | 실행 로그 조회 |

## 배포

### Docker

#### 1. Docker 빌드 및 실행

```bash
# Docker Compose를 이용한 실행
docker compose up --build -d

# 컨테이너 상태 확인
docker ps

# 컨테이너 내부 접근
docker exec -it [container_name] bash

# 서비스 중지
docker compose down
```

### Kubernetes

#### 1. 이미지 빌드 및 배포

```bash
# Docker 이미지 빌드
docker build . -t watcher-backend:latest

# 이미지 저장
docker save -o watcher-backend.tar watcher-backend:latest

# Kubernetes 리소스 배포
kubectl apply -f [yaml파일]

# 배포 스크립트 실행
#config/jcode/image
./deploy_image.sh watcher-backend.tar

# 배포 재시작
kubectl rollout restart -n [namespace] deploy/watcher-backend
```

#### 2. 모니터링 및 관리

```bash
# 파드 상태 모니터링
watch kubectl top po -n [namespace]

# 파드 정보 조회
kubectl get po -n [namespace] -o wide

#로그 조회
kubectl logs -n [namespace] [pod_name] [options]

# 파드 내부 접근
kubectl exec -it -n [namespace] [pod_name] -- bash

# Kubernetes 로그
kubectl logs -f deployment/watcher-backend -n [namespace]
```