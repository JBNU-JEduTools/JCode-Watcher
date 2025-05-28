from sqlmodel import create_engine, SQLModel, Session
from typing import Annotated
from fastapi import Depends
from models.snapshot import Snapshot
from schemas.config import settings
from sqlalchemy import event

db_url = settings.DB_URL
connect_args = {
    "check_same_thread": False,
    "timeout": 60,  # 타임아웃 시간 증가
    "isolation_level": "IMMEDIATE"  # 트랜잭션 격리 수준 설정
}
engine = create_engine(
    db_url, 
    echo=False, 
    connect_args=connect_args,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_size=20,  # 커넥션 풀 크기 설정
    max_overflow=30  # 최대 추가 커넥션 수
)

# @event.listens_for(engine, "connect")
# def _disable_wal(dbapi_conn, conn_record):
#     cursor = dbapi_conn.cursor()
#     cursor.execute("PRAGMA journal_mode=DELETE;")
#     cursor.close()

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
def insert_data():
    with Session(engine) as session:
        snapshots = [
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202511111, filename="aaaa.c", timestamp="20250226_082535", file_size=52),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202522222, filename="bbbb.c", timestamp="20250226_082804", file_size=3),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202533333, filename="cccc.c", timestamp="20250226_082900", file_size=42),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202544444, filename="dddd.c", timestamp="20250226_083000", file_size=99),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202555555, filename="eeee.c", timestamp="20250224_083100", file_size=33),
            Snapshot(class_div="os-1", hw_name="hw2", student_id=202566666, filename="ffff.c", timestamp="20250224_083200", file_size=18),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202577777, filename="gggg.c", timestamp="20250224_083300", file_size=9),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202588888, filename="hhhh.c", timestamp="20250224_083400", file_size=46),
            Snapshot(class_div="os-1", hw_name="hw1", student_id=202599999, filename="iiii.c", timestamp="20250224_083500", file_size=28),
        ]
        
        session.add_all(snapshots)
        session.commit()
    
def get_session():
    # with Session(engine) as session:
    #     yield session
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

# SessionDep = Annotated[Session, Depends(get_session)]