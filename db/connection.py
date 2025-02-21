from sqlmodel import create_engine, SQLModel, Session
from typing import Annotated
from fastapi import Depends

# 해당 경로에 db 파일 없는 경우 자동 생성
sqlite_file_name = "database.db"   # sqlite db 파일 이름
sqlite_url = f"sqlite:////home/ubuntu/backend/app/db/{sqlite_file_name}"   # sqlite db 파일 경로

connect_args = {"check_same_thread": False}   # fastapi에서 여러 스레드에서 동일한 sqlite db 사용 가능  
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)
# echo=True : 모든 sql 문장 출력

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
def get_session():
    with Session(engine) as session:
        yield session

# SessionDep = Annotated[Session, Depends(get_session)]