import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.websocket import manager
from app.db.session import engine, AsyncSessionLocal
from app.models.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield
    # Shutdown
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title="Conjunction Avoidance System",
    description="Autonomous satellite conjunction detection and maneuver planning API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.satellites import router as sat_router
from app.api.conjunctions import router as conj_router

app.include_router(sat_router)
app.include_router(conj_router)


@app.get("/health")
async def health():
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "ok", "version": "1.0.0"}


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send welcome ping
        await manager.send_personal(websocket, {
            "type": "connected",
            "message": "Real-time alerts active",
        })
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()
            if data == "ping":
                await manager.send_personal(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# __init__ files
import os
for path in [
    "app/__init__.py",
    "app/api/__init__.py",
    "app/core/__init__.py",
    "app/db/__init__.py",
    "app/models/__init__.py",
    "app/schemas/__init__.py",
    "app/services/__init__.py",
    "app/workers/__init__.py",
]:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
