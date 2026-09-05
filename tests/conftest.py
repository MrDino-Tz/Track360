import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "test.plant.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AFRICASTALKING_SEND_ACK"] = "false"
# Keep AI offline in tests: no Groq key, so equipment_questions falls back to
# the static menu unless a test explicitly monkeypatches the AI layer.
os.environ["THIBITISHA_GROQ_API_KEY"] = ""

from fastapi.testclient import TestClient
import pytest

from app.config import get_settings

get_settings.cache_clear()

from app.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_equipment
from app.services.conversation import reset_pending


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
    reset_pending()
    with TestClient(app) as test_client:
        yield test_client
