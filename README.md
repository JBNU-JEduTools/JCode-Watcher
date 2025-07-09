# JCode Watcher

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![eBPF](https://img.shields.io/badge/eBPF-00D4AA?style=for-the-badge&logoColor=white)

**교육용 WebIDE 플랫폼의 백그라운드 모니터링 시스템**

JCode Watcher는 [JCode 플랫폼](https://jcode.jbnu.ac.kr)에서 학습자들의 프로그래밍 활동을 실시간으로 모니터링하는 시스템입니다. 브라우저 기반 개발환경에서 학생들이 작성하는 코드와 실행하는 프로세스를 추적하여 학습 데이터를 수집합니다.

**주요 기능**
- 실시간 프로그래밍 활동 추적 및 학습 과정 가시성 제공
- 과제 수행 과정에서의 시행착오와 문제 해결 패턴 분석
- 학습 분석 및 이상 행위 탐지를 위한 행동 데이터 수집


## 아키텍처

### 시스템 구성

JCode Watcher는 **Kubernetes DaemonSet 패턴**으로 설계된 분산 모니터링 시스템입니다. 각 노드에서 독립적으로 실행되면서 해당 노드의 모든 학생 컨테이너를 감시합니다.

```
┌─────────────────────────────────────────────────────────┐
│                  JCode Platform                         │
│  Frontend (WebIDE Interface) + Backend (Container Mgmt) │
└─────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  ┌─────────────────────┐  ┌─────────────────────┐       │
│  │       Node 1        │  │       Node 2        │ ...   │
│  │                     │  │                     │       │
│  │ Watcher (DaemonSet) │  │ Watcher (DaemonSet) │       │
│  │ ├─ filemon          │  │ ├─ filemon          │       │
│  │ │  (inotify)        │  │ │  (inotify)        │       │
│  │ └─ procmon          │  │ └─ procmon          │       │
│  │    (eBPF)           │  │    (eBPF)           │       │
│  │        ↓ 감시        │  │        ↓ 감시       │       │
│  │ ┌─────┐ ┌─────┐     │  │ ┌─────┐ ┌─────┐     │       │
│  │ │Pod A│ │Pod B│ ... │  │ │Pod C│ │Pod D│ ... │       │
│  │ │Web  │ │Web  │     │  │ │Web  │ │Web  │     │       │
│  │ │IDE  │ │IDE  │     │  │ │IDE  │ │IDE  │     │       │
│  │ └─────┘ └─────┘     │  │ └─────┘ └─────┘     │       │
│  └─────────────────────┘  └─────────────────────┘       │
└─────────────────────────────────────────────────────────┘
                             │ REST API
              ┌─────────────────────────────┐
              │    JCode Analytics API      │
              └─────────────────────────────┘
```

### 배포 및 확장성
- **DaemonSet 패턴**: 각 Kubernetes 노드마다 정확히 하나의 Watcher 인스턴스
- **수평 확장**: 노드 추가 시 자동으로 Watcher 인스턴스도 배포
- **장애 격리**: 노드별 독립 실행으로 부분 장애가 전체 시스템에 영향 없음
- **리소스 효율성**: 노드 레벨 모니터링으로 컨테이너당 에이전트 불필요

### 데이터 플로우
1. **이벤트 수집**: filemon(inotify) + procmon(eBPF) 병렬 수집
2. **컨테이너 필터링**: UTS namespace hostname 기반 `jcode-*` 패턴 매칭
3. **데이터 전송**: 각 Watcher → JCode Analytics API (비동기 HTTP)
4. **메트릭 노출**: Prometheus scraping endpoint 제공

## 컴포넌트

### 📁 **filemon** (File Monitor)
소스코드 파일 변경사항을 실시간으로 감시합니다.

**기능:**
- 과제 디렉토리 감시 (hw1~hw10)
- 파일 변경 시 스냅샷 자동 생성
- RESTful API를 통한 데이터 전송
- Prometheus 메트릭 제공


### ⚡ **procmon** (Process Monitor)
eBPF 기술을 활용해 커널 레벨에서 프로세스 실행을 추적하고 분석합니다.

**동작 방식:**
- **컨테이너 식별**: UTS namespace에서 hostname 읽어 `jcode-` 접두어 검증
- **전체 감시**: 대상 컨테이너의 모든 프로세스 실행을 커널에서 실시간 감지
- **선택적 처리**: GCC, CLANG, PYTHON, 과제 실행 파일만 필터링하여 처리
- **비침입적 모니터링**: 호스트 PID namespace 접근으로 컨테이너 내부 수정 없음

**수집 정보:**
- 컴파일러 실행 (gcc, clang, g++ 등) 및 소스 파일 경로
- Python 스크립트 실행 및 인터프리터 버전
- 과제 디렉토리 내 바이너리 실행
- 프로세스 종료 코드, 실행 시간, 명령줄 인수

### 모니터링 대상

**감시 대상:**
```
과목-분반-학번/hw{n}/           # 예: os-1-202012180/hw1/
├── *.c, *.h, *.cpp, *.hpp      # C/C++ 소스 파일
└── *.py                        # Python 스크립트
```

**수집 데이터:**
- **파일 이벤트**: inotify 기반 실시간 파일 변경 감지 (생성/수정/삭제)
- **프로세스 이벤트**: eBPF 기반 시스템 콜 추적 (gcc, clang, python 실행)
- **실행 결과**: 종료 코드, 실행 시간, 명령줄 인수
- **컴파일 메타데이터**: 소스 파일 경로, 컴파일러 옵션, 출력 바이너리

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| **언어** | Python 3.12+ | 전체 애플리케이션 런타임 |
| **파일감시** | Watchdog, inotify | 파일시스템 이벤트 감지 |
| **프로세스감시** | BPF/eBPF, bcc | 커널 레벨 프로세스 추적 |
| **비동기처리** | AsyncIO | 이벤트 루프 및 동시성 처리 |
| **HTTP 클라이언트** | aiohttp | 비동기 API 통신 |
| **메트릭** | Prometheus | 시스템 모니터링 및 관찰성 |
| **컨테이너** | Docker, Kubernetes | 애플리케이션 배포 및 오케스트레이션 |
| **권한 관리** | Linux Capabilities | 최소 권한 보안 모델 |

## 운영 환경

전북대학교 JCloud 인프라의 JEduTools 클러스터에서 실행됩니다. 

Watcher는 각 워커 노드에서 학생 컨테이너들과 함께 실행되며, 호스트 커널에 직접 접근하여 컨테이너 내부의 프로세스 실행과 파일 변경을 감지합니다. 이를 위해 `hostPID` 권한과 `/sys/kernel/debug` 마운트, `SYS_ADMIN`/`SYS_PTRACE` capabilities가 필요합니다.

**클러스터 구성**
- Kubernetes v1.32.0
- Ubuntu 24.04 LTS 노드
- Longhorn 볼륨 2개
  - 웹IDE 워크스페이스 디렉터리 (감시 대상)
  - 스냅샷 저장 공간 (카피본 저장)

**프로젝트 요구사항**
- `hostPID: true` (호스트 PID 네임스페이스 접근)
- `/sys/kernel/debug` 호스트 마운트 (eBPF 실행)
- `SYS_ADMIN`, `SYS_PTRACE` capabilities (커널 추적)


## 개발 및 배포

### 로컬 개발
```bash
# filemon 개발
cd packages/filemon && docker-compose up

# procmon 개발  
cd packages/procmon && docker-compose up
```

### 프로덕션 배포
```bash
# Kubernetes DaemonSet 배포
kubectl apply -f packages/filemon/k8s.yaml
kubectl apply -f packages/procmon/k8s.yaml
```

각 패키지의 상세 개발 가이드는 해당 디렉토리의 README를 참조하세요.
