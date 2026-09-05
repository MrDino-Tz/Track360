from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import dashboard, equipment, health, incidents, webhook
from app.seed import seed_if_empty

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


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
    application.include_router(equipment.router)
    application.include_router(incidents.router)
    application.include_router(dashboard.router)

    if FRONTEND_DIR.exists():
        application.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

        @application.get("/")
        def index() -> FileResponse:
            return FileResponse(FRONTEND_DIR / "index.html")

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
