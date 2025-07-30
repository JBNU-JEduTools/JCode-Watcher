# Watcher - 파일 시스템 감시 및 스냅샷 관리

학생 과제 파일의 변경사항을 실시간으로 감지하고 스냅샷을 생성하는 시스템입니다.

## 🚀 개발환경 설정

### 필수 요구사항

- Docker
- `/home/ubuntu/jcode` 디렉토리 (실제 감시 대상)

### 개발 시작하기

```bash
# 1. 저장소 클론
git clone https://github.com/JBNU-JEduTools/JCode-Watcher.git
cd packages/filemon

# 2. 개발 환경 실행
docker compose up --build

# 3. 로그 확인
docker logs -f watcher-filemon
```

### 개발 워크플로우

```bash
# 코드 수정 후 재시작
docker compose restart watcher-filemon

# 의존성 변경 시 재빌드
docker-compose up --build

# 컨테이너 내부 접근 (디버깅)
docker-compose exec watcher-filemon bash
```
