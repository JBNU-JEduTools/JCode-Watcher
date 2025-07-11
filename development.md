## Watcher 시스템 개발 환경 가이드

### 🎯 개발 환경 목표
JCode Watcher 시스템을 로컬에서 개발하고 테스트할 수 있는 완전한 환경을 구성합니다. 실제 프로덕션 환경과 동일한 방식으로 파일 변경과 프로세스 실행을 모니터링하여 개발 과정에서 시스템 동작을 확인할 수 있습니다.

### 🏗️ 개발 환경 아키텍처

로컬 개발 환경은 총 4개의 컨테이너로 구성됩니다:

**1. watcher-backend**
- 역할: 모든 모니터링 이벤트를 수집하는 REST API 서버
- 포트: 3000번 (외부 접근 가능)
- 데이터베이스: SQLite (로컬 볼륨 마운트)
- 개발 특징: 소스 코드 핫 리로드 지원

**2. watcher-filemon**  
- 역할: 공유 워크스페이스의 파일 변경 실시간 감지
- 포트: 9090번 (메트릭 엔드포인트)
- 감시 대상: code-server 워크스페이스 디렉토리
- 개발 특징: 실시간 로그 출력으로 이벤트 확인

**3. watcher-procmon**
- 역할: 워크스페이스 내 프로세스 실행 추적
- 포트: 9091번 (메트릭 엔드포인트) 
- 특수 권한: eBPF 실행을 위한 호스트 권한 필요
- 개발 특징: gcc, python 등 개발 도구 실행 감지

**4. code-server (LinuxServer.io)**
- 역할: 브라우저 기반 통합 개발 환경 (VS Code)
- 포트: 8443번 (HTTPS 웹 인터페이스)
- 워크스페이스: 다른 서비스와 공유되는 개발 디렉토리
- 개발 특징: 실제 학생 환경과 동일한 WebIDE

### ✅ 사전 요구사항 확인

개발 환경을 시작하기 전에 다음 사항들을 확인해야 합니다.

#### 1. Docker 및 Docker Compose 설치 확인
```bash
docker --version
docker-compose --version
```

다음과 같이 출력되어야 합니다:
```
Docker version 20.10.0 또는 이상
docker-compose version 1.29.0 또는 이상
```

#### 2. 포트 사용 상태 확인
개발 환경에서 사용할 포트들이 비어있는지 확인합니다:

```bash
# 사용 중인 포트 확인
netstat -tulpn | grep -E ":(3000|8443|9090|9091)"
```

아무것도 출력되지 않아야 합니다. 만약 포트가 사용 중이면 해당 프로세스를 종료하거나 docker-compose.yml에서 포트를 변경하세요.

#### 3. eBPF 지원 확인 (procmon용)
```bash
# 커널 버전 확인 (4.9 이상 필요)
uname -r

# debugfs 마운트 확인
mount | grep debugfs
```

정상적인 경우:
```
debugfs on /sys/kernel/debug type debugfs (rw,nosuid,nodev,noexec,relatime)
```

### 📁 1단계: 프로젝트 준비

#### 코드 복제 및 디렉토리 이동
```bash
git clone https://github.com/JBNU-JEduTools/JCode-Watcher.git
cd JCode-Watcher
```

#### 개발 환경용 디렉토리 구조 생성
```bash
# 개발용 워크스페이스 디렉토리 생성
mkdir -p dev-workspace/{hw1,hw2,hw3,projects}
mkdir -p dev-data/{backend-db,filemon-snapshots}
mkdir -p dev-logs
```

생성된 디렉토리 구조를 확인합니다:
```bash
tree dev-workspace dev-data -L 2
```

다음과 같이 출력되어야 합니다:
```
dev-workspace/
├── hw1/
├── hw2/
├── hw3/
└── projects/
dev-data/
├── backend-db/
└── filemon-snapshots/
```

### 🐳 2단계: Docker Compose 환경 구성

#### Docker Compose 설정 확인
프로젝트 루트에 이미 준비된 개발 환경용 Docker Compose 파일을 확인합니다:

```bash
ls -la docker-compose.dev.yml
```

파일이 존재하는지 확인하고, 내용을 검토해보세요:

```bash
cat docker-compose.dev.yml
```

이 설정 파일에는 다음 4개 서비스가 정의되어 있습니다:
- **watcher-backend**: API 서버 (포트 3000)
- **watcher-filemon**: 파일 모니터링 (포트 9090) 
- **watcher-procmon**: 프로세스 모니터링 (포트 9091)
- **code-server**: WebIDE (포트 8443)

#### 개발용 샘플 파일 생성
테스트를 위한 샘플 코드를 준비합니다:

```bash
# C 언어 샘플
cat > dev-workspace/hw1/hello.c << 'EOF'
#include <stdio.h>

int main() {
    printf("Hello Watcher Development!\n");
    printf("This file is being monitored by filemon service.\n");
    return 0;
}
EOF

# Python 샘플
cat > dev-workspace/hw2/calculator.py << 'EOF'
#!/usr/bin/env python3

def add(a, b):
    return a + b

def main():
    print("Python Calculator - Monitored by Watcher")
    result = add(10, 20)
    print(f"10 + 20 = {result}")

if __name__ == "__main__":
    main()
EOF
```

### 🚀 3단계: 개발 환경 시작

#### 모든 서비스 시작
준비된 Docker Compose 설정으로 전체 개발 환경을 한 번에 시작합니다:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

빌드 및 시작 과정에서 다음과 같은 로그들이 출력됩니다:

```
Building watcher-backend...
Building watcher-filemon...
Building watcher-procmon...
Pulling code-server...

Creating watcher-backend...
Creating watcher-filemon...
Creating watcher-procmon...
Creating code-server...

watcher-backend | Server starting on port 3000
watcher-backend | Database initialized successfully
watcher-filemon | Starting file monitoring on /watcher/codes
watcher-filemon | Watching directories: ['hw1', 'hw2', 'hw3', 'projects']
watcher-procmon | BPF programs loaded successfully
code-server | Web interface available at https://localhost:8443
```

**백그라운드 실행:** 로그를 보지 않고 백그라운드에서 실행하려면:
```bash
docker-compose -f docker-compose.dev.yml up --build -d
```

### ✅ 4단계: 개발 환경 접근 및 확인

#### 서비스 상태 확인
```bash
docker-compose -f docker-compose.dev.yml ps
```

모든 서비스가 `Up` 상태여야 합니다:
```
       Name                     Command               State           Ports
---------------------------------------------------------------------------
watcher-backend     node /app/src/index.js           Up      0.0.0.0:3000->3000/tcp
watcher-filemon     python3 -m src.app               Up      0.0.0.0:9090->9090/tcp
watcher-procmon     python3 -m src.app               Up      0.0.0.0:9091->9090/tcp
code-server         /init                            Up      0.0.0.0:8443->8443/tcp
```

#### WebIDE 접속
브라우저에서 `https://localhost:8443`에 접속합니다.

- **비밀번호**: `watcher123`
- **워크스페이스**: `/config/workspace` (자동으로 열림)

접속하면 다음과 같은 구조로 파일들이 보입니다:
```
workspace/
├── hw1/
│   └── hello.c
├── hw2/
│   └── calculator.py
├── hw3/
└── projects/
```

#### API 서버 헬스체크
```bash
curl http://localhost:3000/health
```

정상적인 응답:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "services": {
    "database": "connected",
    "filesystem": "accessible"
  }
}
```

#### 메트릭 엔드포인트 확인
```bash
# 파일 모니터링 메트릭
curl http://localhost:9090/metrics | grep file_events

# 프로세스 모니터링 메트릭  
curl http://localhost:9091/metrics | grep process_events
```

### 🧪 5단계: 실제 모니터링 테스트

이제 실제로 시스템이 동작하는지 테스트해보겠습니다.

#### 파일 변경 모니터링 테스트

**1단계**: Code Server에서 파일 편집
- WebIDE에서 `hw1/hello.c` 파일을 열어서 수정해보세요
- 예를 들어, printf 문을 추가하거나 변경해보세요

**2단계**: filemon 로그 확인
```bash
docker-compose -f docker-compose.dev.yml logs -f watcher-filemon
```

다음과 같은 로그가 실시간으로 출력됩니다:
```
watcher-filemon | [2024-01-01 12:00:00] File event detected: MODIFY /watcher/codes/hw1/hello.c
watcher-filemon | [2024-01-01 12:00:00] Snapshot created: hello.c.1704067200.snapshot
watcher-filemon | [2024-01-01 12:00:00] Event sent to API: POST /api/events/file
```

**3단계**: 스냅샷 파일 확인
```bash
ls -la dev-data/filemon-snapshots/
```

파일을 수정할 때마다 스냅샷이 생성되는 것을 확인할 수 있습니다.

#### 프로세스 실행 모니터링 테스트

**1단계**: Code Server 터미널에서 컴파일 및 실행
WebIDE에서 터미널을 열고 다음을 실행:

```bash
cd hw1
gcc hello.c -o hello
./hello
```

**2단계**: procmon 로그 확인
```bash
docker-compose -f docker-compose.dev.yml logs -f watcher-procmon
```

다음과 같은 로그가 출력됩니다:
```
watcher-procmon | [2024-01-01 12:01:00] Process executed: gcc [hello.c, -o, hello]
watcher-procmon | [2024-01-01 12:01:00] Process PID: 12345, Exit code: 0
watcher-procmon | [2024-01-01 12:01:01] Process executed: ./hello []
watcher-procmon | [2024-01-01 12:01:01] Process PID: 12346, Exit code: 0
watcher-procmon | [2024-01-01 12:01:01] Event sent to API: POST /api/events/process
```

**3단계**: Python 실행 테스트
```bash
cd ../hw2
python3 calculator.py
```

Python 실행도 감지되는 것을 확인할 수 있습니다.

#### 수집된 데이터 확인

**API를 통한 이벤트 조회:**
```bash
# 최근 파일 이벤트 조회
curl "http://localhost:3000/api/events/file?limit=10"

# 최근 프로세스 이벤트 조회  
curl "http://localhost:3000/api/events/process?limit=10"
```

**메트릭 통계 확인:**
```bash
# 파일 이벤트 통계
curl http://localhost:9090/metrics | grep -E "(file_events_total|file_modifications)"

# 프로세스 이벤트 통계
curl http://localhost:9091/metrics | grep -E "(process_executions_total|compilation_events)"
```

### 📊 6단계: 개발 도구 및 디버깅

#### 실시간 로그 모니터링
모든 서비스의 로그를 동시에 확인:

```bash
docker-compose -f docker-compose.dev.yml logs -f
```

특정 서비스만 확인:
```bash
# 백엔드만
docker-compose -f docker-compose.dev.yml logs -f watcher-backend

# 파일 모니터링만
docker-compose -f docker-compose.dev.yml logs -f watcher-filemon
```

#### 컨테이너 내부 접근
디버깅이 필요한 경우 컨테이너에 직접 접속:

```bash
# 백엔드 컨테이너 접속
docker-compose -f docker-compose.dev.yml exec watcher-backend bash

# filemon 컨테이너 접속  
docker-compose -f docker-compose.dev.yml exec watcher-filemon bash
```

#### 데이터베이스 직접 확인
```bash
# SQLite 데이터베이스 확인
docker-compose -f docker-compose.dev.yml exec watcher-backend sqlite3 /app/data/watcher.db

# 테이블 목록
.tables

# 최근 이벤트 조회
SELECT * FROM file_events ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM process_events ORDER BY timestamp DESC LIMIT 5;
```

### 🔧 문제 해결 가이드

#### 서비스가 시작되지 않는 경우

**포트 충돌:**
```bash
# 사용 중인 포트 확인 및 해제
sudo lsof -i :3000
sudo lsof -i :8443
sudo lsof -i :9090
sudo lsof -i :9091
```

**권한 문제 (procmon):**
```bash
# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인

# 또는 sudo로 실행
sudo docker-compose -f docker-compose.dev.yml up
```

#### Code Server 접속 불가

**방화벽 확인:**
```bash
# 8443 포트 방화벽 확인
sudo ufw status | grep 8443

# 필요시 포트 허용
sudo ufw allow 8443
```

**컨테이너 상태 확인:**
```bash
docker-compose -f docker-compose.dev.yml logs code-server
```

#### 파일 감지가 안 되는 경우

**볼륨 마운트 확인:**
```bash
# filemon 컨테이너에서 워크스페이스 확인
docker-compose -f docker-compose.dev.yml exec watcher-filemon ls -la /watcher/codes
```

**inotify 제한 확인:**
```bash
# inotify 설정 확인
cat /proc/sys/fs/inotify/max_user_watches

# 필요시 제한 증가
echo 'fs.inotify.max_user_watches=524288' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 🛠️ 개발 워크플로우

#### 코드 변경 시 재시작
소스 코드를 수정한 후 변경사항을 반영하려면:

```bash
# 특정 서비스만 재빌드 및 재시작
docker-compose -f docker-compose.dev.yml up --build --no-deps watcher-backend

# 모든 서비스 재빌드
docker-compose -f docker-compose.dev.yml up --build --force-recreate
```

#### 개발 환경 정리
```bash
# 컨테이너 중지 및 제거
docker-compose -f docker-compose.dev.yml down

# 볼륨까지 제거 (데이터 삭제)
docker-compose -f docker-compose.dev.yml down -v

# 이미지까지 제거
docker-compose -f docker-compose.dev.yml down --rmi all
```

### 🎉 개발 환경 완료!

이제 완전한 Watcher 개발 환경이 구성되었습니다!

**✅ 사용 가능한 기능들:**
- **실시간 파일 모니터링**: Code Server에서 파일 편집 시 즉시 감지
- **프로세스 실행 추적**: gcc, python 등 개발 도구 실행 모니터링  
- **웹 기반 IDE**: 실제 학습 환경과 동일한 VS Code 인터페이스
- **API 데이터 수집**: 모든 이벤트가 백엔드 API로 전송되어 저장
- **실시간 메트릭**: Prometheus 형식의 모니터링 지표
- **핫 리로드**: 소스 코드 변경 시 자동 반영

**🔗 접속 주소 요약:**
- **WebIDE**: https://localhost:8443 (비밀번호: watcher123)
- **백엔드 API**: http://localhost:3000
- **파일 모니터링 메트릭**: http://localhost:9090/metrics
- **프로세스 모니터링 메트릭**: http://localhost:9091/metrics

이제 실제 JCode 플랫폼과 동일한 방식으로 학습자 모니터링 시스템을 개발하고 테스트할 수 있습니다!
