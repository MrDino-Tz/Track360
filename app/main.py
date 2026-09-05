from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import ai_chat, dashboard, equipment, health, incidents, rewards, sms_sync, ussd, webhook
from app.seed import seed_if_empty

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="1.0.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(webhook.router)
    application.include_router(ussd.router)
    application.include_router(sms_sync.router)
    application.include_router(equipment.router)
    application.include_router(incidents.router)
    application.include_router(rewards.router)
    application.include_router(dashboard.router)
    application.include_router(ai_chat.router)

    # The React app is served last so API/webhook/health routes keep precedence.
    # HashRouter means all client-side routes live under `#/`, so no SPA
    # fallback is needed — only the built index.html and its /assets files.
    if FRONTEND_DIST.exists():
        application.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return application


def init_db() -> None:
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


init_db()
app = create_app()
