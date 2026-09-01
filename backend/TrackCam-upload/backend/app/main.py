"""
TrackCam Backend — FastAPI application entrypoint.

Stage 2 scope (current):
    - App factory + lifespan startup/shutdown logging
    - CORS configured for the existing (unmodified) frontend
    - Structured logging
    - /health and / endpoints
    - DB connectivity check surfaced in /health (does not crash the app if
      the database is unreachable — degraded status is reported instead)

Later stages will `include_router(...)` the cameras/anpr/tracking/traffic/
alerts routers here, mount /ws/live, and start the model manager.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    alerts,
    cameras,
    detections,
    frames,
    license_plates,
    stats,
    vehicle_events,
    vehicles,
    videos,
)
from app.config import settings
from app.database.connection import check_database_connection
from app.utils.logger import get_logger, setup_logging

# Importing app.models registers every ORM model on Base.metadata — required
# before any create_all()/Alembic autogenerate call, and before the routers
# below execute any query.
import app.models  # noqa: F401

setup_logging(level=settings.LOG_LEVEL, json_output=settings.LOG_JSON)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------------------------------------------------------------- startup
    logger.info(
        "Starting %s v%s [%s]",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    logger.info("CORS allowed origins: %s", settings.cors_origins)

    db_ok, db_error = check_database_connection()
    if db_ok:
        logger.info("Database connection OK")
    else:
        logger.warning(
            "Database is not reachable at startup — API will still boot, "
            "but data-backed endpoints will fail until DB is available. Error: %s",
            db_error,
        )

    # Model manager, YOLO/plate/OCR/ReID/LSTM loading, and video worker
    # startup are wired in from Stage 3 onward.

    yield

    # --------------------------------------------------------------- shutdown
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend API for TrackCam — AI-Based Multi-Camera Traffic Intelligence "
        "System. Provides ANPR, multi-camera vehicle tracking, traffic "
        "prediction, and alerting data to the existing TrackCam frontend."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Last-resort handler so unexpected errors never leak stack traces or
    internal details to the frontend. Specific, well-typed error handling
    for model/video/db failures is added alongside each module in later
    stages (see app/utils and per-router exception handlers).
    """
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please check backend logs."},
    )


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Meta"])
def health() -> dict:
    """
    Health/readiness check.

    Returns HTTP 200 even in a degraded state (e.g. DB down) so container
    orchestrators don't kill the process during a transient DB outage —
    the `status` field communicates the real state to callers/monitors.
    """
    db_ok, db_error = check_database_connection()

    return {
        "status": "ok" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
        # Populated from Stage 3 onward once the model manager exists.
        "models": "not_initialized",
    }


app.include_router(cameras.router, prefix="/api/cameras", tags=["Cameras"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(frames.router, prefix="/api/frames", tags=["Frames"])
app.include_router(detections.router, prefix="/api/detections", tags=["Detections"])
app.include_router(license_plates.router, prefix="/api/license-plates", tags=["License Plates"])
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["Vehicles"])
app.include_router(vehicle_events.router, prefix="/api/vehicle-events", tags=["Vehicle Events"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])

# ---------------------------------------------------------------------------
# Not yet implemented — added in later stages once the AI/CV modules exist:
#
# from app.api import anpr, tracking, traffic
# app.include_router(anpr.router, prefix="/api/anpr", tags=["ANPR"])
# app.include_router(tracking.router, prefix="/api/tracking", tags=["Tracking"])
# app.include_router(traffic.router, prefix="/api/traffic", tags=["Traffic"])
#
# from app.websocket.manager import router as ws_router
# app.include_router(ws_router)
# ---------------------------------------------------------------------------
