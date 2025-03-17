# Watcher - backend

## 파일 구조
 FastAPI 공식 문서 파일 구조 예시

https://fastapi.tiangolo.com/tutorial/bigger-applications/

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 애플리케이션의 메인 진입점
│   ├── dependencies.py  # 의존성 주입 관련(경로 동작 함수에 필요한 의존성 정의)
│   ├── routers/         # API 라우터 디렉토리
│   │   ├── __init__.py
│   │   ├── example.py
│   │   └── example2.py
│   ├── internal/        # 내부에서만 사용되는 코드 정의 - admin 기능/필요한 비즈니스 로직 등등
│   │   ├── __init__.py
│   │   └── admin.py
│   ├── db/              # DB 관련 파일 디렉토리
│   │   ├── base.py      # SQLAlchemy 모델 정의 기본 클래스 : Base = declarative_base() 등
│   │   ├── session.py   # DB 연결 엔진, DB 세션 관리
│   │   └── migrations/  # Alembic 마이그레이션 폴더
│   ├── models/          # SQLAlchemy 모델 정의
│   │   ├── example.py
│   │   └── example2.py
│   ├── schemas/         # Pydantic 모델 정의 - API 요청, 응답 데이터 구조 관리
│   │   ├── example.py
│   │   └── example2.py
│   └── crud/            # CRUD 작업 정의(DB 처리 로직)
│   │   ├── example.py
│   │   └── example2.py
│   └── services/        # 비즈니스 로직 정의
│   │   ├── example.py
│   │   └── example2.py
```


## 시작하기

--reload : 코드 변경 시 자동 리로드(개발환경에서만 사용)

```
pip install "fastapi[all]"

pip install sqlmodel

uvicorn main:app --reload --port 3000 --host 0.0.0.0
```

- FastAPI 공식문서 tutorial : https://fastapi.tiangolo.com/tutorial/

- /docs 에서 api 문서 확인 가능 - swagger


## Tools
- FastAPI