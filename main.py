"""
PI Darts Counter - FastAPI Backend
Main application entry point.
"""
import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api import router, websocket_endpoint

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="PI Darts Counter API",
    description="Backend API for automated darts scoring system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routes
app.include_router(router)


# WebSocket endpoint
@app.websocket("/ws/{game_id}")
async def websocket_handler(websocket: WebSocket, game_id: str):
    """
    WebSocket endpoint for real-time game updates.

    Args:
        websocket: WebSocket connection
        game_id: Game UUID
    """
    await websocket_endpoint(websocket, game_id)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "PI Darts Counter API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("PI Darts Counter API starting...")
    logger.info(f"Server: {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Default game mode: {settings.default_mode}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("PI Darts Counter API shutting down...")