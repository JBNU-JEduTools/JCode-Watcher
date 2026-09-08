from db.url import normalize_database_url
from schemas.config import settings
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

db_url = normalize_database_url(settings.DB_URL)


def build_engine(url: str):
    url = normalize_database_url(url)
    options = {"echo": False, "pool_pre_ping": True}
    if url.startswith("sqlite:"):
        options["connect_args"] = {
            "check_same_thread": False,
            "timeout": 60,
            "isolation_level": "IMMEDIATE",
        }
    else:
        options.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
        )
    return create_engine(url, **options)


engine = build_engine(db_url)

# @event.listens_for(engine, "connect")
# def _disable_wal(dbapi_conn, conn_record):
#     cursor = dbapi_conn.cursor()
#     cursor.execute("PRAGMA journal_mode=DELETE;")
#     cursor.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def check_database() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_session():
    # with Session(engine) as session:
    #     yield session
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


# SessionDep = Annotated[Session, Depends(get_session)]
