"""FastAPI app instance, router registration, static file mounts, and startup hooks."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.mongodb import close_db, connect_db, ensure_indexes
from app.routers import activity, auth, dashboard, disposal, recyclers, scan, suggestions
from seed.seed_recyclers import seed_recyclers
from seed.seed_disposal_guides import seed_disposal_guides

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_FOLDER = Path(settings.upload_dir)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="WasteWise API", version="0.1.0")

# Same-origin serving means CORS is not strictly required, but we keep a permissive
# policy so the API stays usable from any dev tool / separate origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    db = await connect_db()
    await ensure_indexes()
    await seed_recyclers(db)
    await seed_disposal_guides(db)
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_db()


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": "wastewise"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Make authentication the default entry point for the product."""
    return RedirectResponse(url="/login.html", status_code=307)


app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(scan.router, prefix="/api", tags=["scan"])
app.include_router(suggestions.router, prefix="/api", tags=["suggestions"])
app.include_router(recyclers.router, prefix="/api", tags=["recyclers"])
app.include_router(disposal.router, prefix="/api", tags=["disposal"])
app.include_router(activity.router, prefix="/api", tags=["activity"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])

# Mount uploaded images so the frontend can preview scan photos.
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_FOLDER)), name="uploads")

# Serve the static frontend (PWA) last so /api/* takes precedence.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
