# Watcher-bakcend : 프로그래밍 활동 저장 및 분석

**Watcher**는 학생들의 코딩 과제 수행 과정을 실시간으로 저장, 분석하는 FastAPI 기반의 백엔드 시스템입니다.

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/docs.html)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/doc/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://kubernetes.io/ko/docs/home/)

## 주요 기능

- **코드 스냅샷 추적**: 학생들의 코드 변경 사항을 실시간으로 기록
- **학습 분석**: 학생별/과제별 코딩 패턴 및 통계 분석
- **로그 모니터링**: 빌드 및 실행 로그 추적
- **메트릭 수집**: Prometheus를 통한 시스템 모니터링
- **API문서** : /docs (스웨거 문서 자동 작성)

## 파일 구조

```
app/
├── crud/                 # CRUD 작업 정의(DB 처리 로직)
├── data/                 # 데이터 파일 저장소
│   └── example.db
├── db/                   # DB 연결 및 세션 관리리
│   └── connection.py
├── dev/                  # Kubernetes 테스트용 yaml 파일
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

## 구조
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

## 배포 및 테스트

**실행**
```
pip install "fastapi[all]"

pip install sqlmodel

uvicorn main:app --reload --port 3000 --host 0.0.0.0
```

**Docker**
```
docker ps

docker compose up --build -d

docker exec [container] [command]

docker compose down
```

**Kubernetes**

- 배포
```
docker build . -t watcher-backend:latest

docker save -o watcher-backend.tar watcher-backend:latest

#리소스 정의
kubectl apply -f [yaml파일]

#config/jcode/image
./deploy_image.sh watcher-backend.tar

kubectl rollout restart -n [namespace] deploy/watcher-backend
```

- 모니터링
```
watch kubectl top po -n [namespace]

kubectl get po -n [namespace] -o wide

#로그 조회
kubectl logs -n [namespace] [pod_name] [options]

#파드 안의 컨테이너에서 명령 실행
kubectl exec -it -n [namespace] [pod_name] [-- command [args...]] 
```