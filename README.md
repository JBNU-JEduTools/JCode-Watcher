# JCode Watcher

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![eBPF](https://img.shields.io/badge/eBPF-00D4AA?style=for-the-badge&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)

**교육용 WebIDE 플랫폼의 백그라운드 모니터링 시스템**

JCode Watcher는 [JCode 플랫폼](https://jcode.jbnu.ac.kr)에서 학습자들의 프로그래밍 활동을 실시간으로 모니터링하는 시스템입니다. 브라우저 기반 개발환경에서 학생들이 작성하는 코드와 실행하는 프로세스를 추적하여 학습 데이터를 수집합니다.

**주요 기능**
- 실시간 프로그래밍 활동 추적 및 학습 과정 가시성 제공
- 과제 수행 과정에서의 시행착오와 문제 해결 패턴 분석
- 학습 분석 및 이상 행위 탐지를 위한 행동 데이터 수집

## 아키텍처

### 시스템 구성

JCode Watcher는 Kubernetes DaemonSet 패턴으로 설계된 분산 모니터링 시스템입니다. 각 노드에서 독립적으로 실행되면서 해당 노드의 모든 학생 컨테이너를 감시합니다.

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

### 데이터 플로우
1. **이벤트 수집**: filemon(inotify) + procmon(eBPF) 병렬 수집
2. **컨테이너 식별**: 학생 컨테이너만 선별적 모니터링
3. **데이터 전송**: 각 Watcher → JCode Analytics API (비동기 HTTP)
4. **메트릭 노출**: Prometheus scraping endpoint 제공

## 컴포넌트

### 📁 **filemon** (File Monitor)
inotify 기반으로 학생 워크스페이스의 파일 변경사항을 실시간 추적합니다.

**동작 방식:**
- **디렉토리 감시**: 과제 디렉토리 (hw1~hw10) 실시간 모니터링
- **이벤트 필터링**: C/C++/Python 소스 파일만 선별적 감지
- **스냅샷 생성**: 파일 변경 시점의 전체 코드 백업
- **비동기 전송**: 변경 이벤트를 Analytics API로 실시간 전송

**수집 정보:**
- 파일 생성/수정/삭제 이벤트와 타임스탬프
- 파일 경로 및 크기 변화
- 코드 변경사항 diff 정보
- Prometheus 메트릭 (파일 이벤트 수, 처리 시간)


### ⚡ **procmon** (Process Monitor)
eBPF 기반으로 컨테이너 내 프로세스 실행을 커널에서 추적합니다.

**동작 방식:**
- **컨테이너 식별**: hostname 기반 대상 컨테이너 필터링
- **프로세스 추적**: gcc, python 등 개발 관련 프로세스만 감지
- **실행 정보 수집**: 명령줄 인수, 종료 코드, 실행 시간
- **커널 레벨 감시**: 컨테이너 내부 수정 없이 비침입적 모니터링

**수집 정보:**
- 컴파일러 실행 정보 (gcc, clang, g++ 등)
- Python 스크립트 실행 및 인터프리터 버전
- 과제 디렉토리 내 바이너리 실행 이벤트
- 프로세스 종료 코드, 실행 시간, 명령줄 인수


## 기술 스택

| 구분 | 기술 | 담당 컴포넌트 |
|------|------|-------------|
| **파일감시** | inotify/Watchdog | filemon |
| **프로세스감시** | eBPF/bcc | procmon |
| **데이터전송** | aiohttp | 공통 |
| **메트릭** | Prometheus | 공통 |
| **컨테이너** | Docker, Kubernetes | 배포환경 |


## 관련 프로젝트

### 기존 프로젝트
- **[Watcher](https://github.com/JBNU-JEduTools/Watcher)** - 클라이언트-서버 기반 코드 변경 이력 추적 시스템 (C/Shell 구현)

### JCode 플랫폼
- **[JCode-Frontend](https://github.com/JBNU-JEduTools/JCode-Frontend)** - JCode 플랫폼 프론트엔드
- **[JCode-Backend](https://github.com/JBNU-JEduTools/JCode-Backend)** - JCode 플랫폼 백엔드
