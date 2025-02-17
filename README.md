# Watcher - backend

## Tools
- FastAPI
- MYSQL


## 파일 구조
 FastAPI 공식 문서 파일 구조 예시

https://fastapi.tiangolo.com/tutorial/bigger-applications/

```
.
├── app
│   ├── main.py          # FastAPI 애플리케이션의 메인 진입점
│   ├── dependencies.py
│   ├── routers          # API 라우터 디렉토리
│   │   ├── example.py
│   │   └── example2.py
│   └── internal
│       ├── __init__.py
│       └── admin.py
```

- db 관련 파일 구조 추가 필요

## 시작하기

--reload : 코드 변경 시 자동 리로드(개발환경에서만 사용)

```
pip install "fastapi[all]"

uvicorn main:app --reload
```