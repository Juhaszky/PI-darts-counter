"""
PI Darts Counter - FastAPI Backend
Main application entry point.
"""
import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api import router, websocket_endpoint
from database import init_db
from camera.camera_manager import CameraManager
import camera.camera_loop as camera_loop

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

# Global camera manager instance — accessed by api/routes.py via lazy import.
camera_manager: CameraManager | None = None


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
    global camera_manager

    logger.info("PI Darts Counter API starting...")
    logger.info("Server: %s:%s", settings.host, settings.port)
    logger.info("Debug mode: %s", settings.debug)
    logger.info("Default game mode: %s", settings.default_mode)

    # Initialize database
    await init_db()

    # Build the camera manager with configured sources (device indices or URLs).
    sources = [
        settings.camera_0_source,
        settings.camera_1_source,
        settings.camera_2_source,
    ]
    camera_manager = CameraManager(sources, fps=settings.camera_fps)

    # Wire the detection loop with its dependencies before trying to start it.
    # _coordinate_mapper is the shared singleton already instantiated in websocket.py.
    from api.websocket import _coordinate_mapper
    camera_loop.setup(camera_manager, _coordinate_mapper)

    # Only open cameras and run the loop when OpenCV is available.
    # On Windows dev machines without OpenCV installed this block is skipped
    # so the rest of the server (REST API, WebSocket, game logic) works normally.
    try:
        import cv2  # noqa: F401  — existence check only
        await camera_manager.start()
        await camera_loop.start()
        logger.info("Camera detection loop running.")
    except ImportError:
        logger.warning(
            "OpenCV not available — camera detection disabled. "
            "Manual throws and mobile camera_frame WebSocket messages still work."
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("PI Darts Counter API shutting down...")
    await camera_loop.stop()
    if camera_manager is not None:
        await camera_manager.stop()
    logger.info("PI Darts Counter API shut down.")
