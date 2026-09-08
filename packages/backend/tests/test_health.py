import main
import pytest
from db.connection import build_engine
from db.url import normalize_database_url
from fastapi.testclient import TestClient


def test_liveness_does_not_depend_on_database(monkeypatch):
    monkeypatch.setattr(
        main, "check_database", lambda: (_ for _ in ()).throw(RuntimeError("down"))
    )
    client = TestClient(main.app)
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503


def test_database_driver_accepts_cnpg_uri_and_restricts_other_drivers():
    sqlite_engine = build_engine("sqlite://")
    assert sqlite_engine.dialect.name == "sqlite"
    sqlite_engine.dispose()
    assert normalize_database_url("postgresql://user:pass@db/watcher") == (
        "postgresql+psycopg://user:pass@db/watcher"
    )
    with pytest.raises(RuntimeError, match="DB_URL"):
        build_engine("mysql+pymysql://watcher:watcher@localhost/watcher")
