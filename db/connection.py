from sqlmodel import create_engine, SQLModel, Session
from typing import Annotated
from fastapi import Depends
from app.models.snapshot import Snapshot

# 해당 경로에 db 파일 없는 경우 자동 생성
sqlite_file_name = "database.db"   # sqlite db 파일 이름
# sqlite_url = f"sqlite:////home/ubuntu/backend/app/db/{sqlite_file_name}"   # sqlite db 파일 경로
sqlite_url = f"sqlite:///app/db/{sqlite_file_name}"

connect_args = {"check_same_thread": False}   # fastapi에서 여러 스레드에서 동일한 sqlite db 사용 가능  
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)
# echo=True : 모든 sql 문장 출력

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
def insert_data():
    with Session(engine) as session:
        snapshots = [
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202012180, filename="test.c", timestamp="20250221_082535", file_size=9),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202012180, filename="test.c", timestamp="20250221_082804", file_size=14),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202012180, filename="test.c", timestamp="20250221_082900", file_size=12),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202012180, filename="test.c", timestamp="20250221_083000", file_size=18),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202012180, filename="test.c", timestamp="20250221_083100", file_size=21),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202012180, filename="test.c", timestamp="20250221_083200", file_size=15),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202012180, filename="test.c", timestamp="20250221_083300", file_size=20),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202012180, filename="test.c", timestamp="20250221_083400", file_size=30),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202012180, filename="test.c", timestamp="20250221_083500", file_size=25),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202012180, filename="test.c", timestamp="20250221_083600", file_size=28)
        ]
        
        session.add_all(snapshots)
        session.commit()
    
def get_session():
    with Session(engine) as session:
        yield session

# SessionDep = Annotated[Session, Depends(get_session)]