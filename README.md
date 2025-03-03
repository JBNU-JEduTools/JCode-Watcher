# Watcher - backend

## Tools
- FastAPI
- SQLite


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

## DB 확인

```
sqlite3 database.db

> .tables   # 테이블 목록 확인

> SELECT * FROM snapshot;  # 테이블 데이터 확인
```


### ToDo

- bytes 표시 -> B, 회차 표시

- 스냅샷 내용 조회 시 vscode 처럼 왼쪽에 스냅샷 목록 -> 선택 시 내용 조회 & 버튼 클릭 시 차례대로 보여주도록
    - 스냅샷 내용 조회 시 nginx 설정

- 첫 타임스탬프 & 마지막 타임스탬프 :프런트에서 가져온 그래프 데이터 활용
    - 총 작업 시간 & 쉬는시간(간격)

- 학생별 watcher 접근 시 코드 파일 목록 default는 전체 - 명시적으로 띄우기

- 스크롤 시 정해진 자리로 이동

- 코드 디렉터리 depth 고려(@)해 수정

- docker
    - docker build -t watcher_back .
    - docker run -p 3000:3000 -v $(pwd)/db:/app/db --env-file .env --name watcher_back_container watcher_back


