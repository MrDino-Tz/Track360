import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "test.plant.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AFRICASTALKING_SEND_ACK"] = "false"

from fastapi.testclient import TestClient
import pytest

from app.config import get_settings

get_settings.cache_clear()

from app.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_equipment


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    if TEST_DB.exists():
        try:
            TEST_DB.unlink()
        except OSError:
            pass


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_equipment(db)
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    _reset_db()
    with TestClient(app) as test_client:
        yield test_client
