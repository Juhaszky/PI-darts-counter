"""
REST API routes for PI Darts Counter.
Handles game lifecycle, player management, and manual throw input.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from models import (
    GameCreate,
    GameCreateResponse,
    GameResponse,
    PlayerResponse,
    ThrowCreate,
)
from game import GameManager
from services.game_service import GameService
from database.db import get_db
from api.websocket import _coordinate_mapper

router = APIRouter(prefix="/api", tags=["games"])


def get_game_manager() -> GameManager:
    """Dependency to get GameManager singleton."""
    return GameManager.get_instance()

def get_game_service() -> GameService:
    manager = get_game_manager()
    return GameService(manager)  # inject GameService as a dependency

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "PI Darts Counter API",
    }


@router.post("/games", response_model=GameCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_game(game_data: GameCreate):
    """
    Create a new game with players.

    Args:
        game_data: Game creation data with mode, double_out, and players

    Returns:
        Game creation response with game_id
    """
    manager = get_game_manager()
    game, players = manager.create_game(game_data)

    return GameCreateResponse(
        game_id=game.id,
        mode=game.mode,
        status=game.status,
        created_at=game.created_at,
    )


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(game_id: str):
    """
    Get game state by ID.

    Args:
        game_id: Game UUID

    Returns:
        Complete game state
    """
    manager = get_game_manager()
    game = manager.get_game(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    players = manager.get_players(game_id)
    current_player = manager.get_current_player(game_id)

    player_responses = [
        PlayerResponse(
            id=p.id,
            name=p.name,
            score=p.score,
            throws_this_turn=p.throws_this_turn,
            is_current=p.is_current,
        )
        for p in players
    ]

    return GameResponse(
        game_id=game.id,
        mode=game.mode,
        status=game.status,
        round=game.round,
        double_out=game.double_out,
        players=player_responses,
        current_player_id=current_player.id if current_player else None,
        winner_id=game.winner_id,
        created_at=game.created_at,
        finished_at=game.finished_at,
    )


@router.post("/games/{game_id}/start")
async def start_game(game_id: str):
    """
    Start a game (transition from waiting to in_progress).

    Args:
        game_id: Game UUID

    Returns:
        Success message
    """
    manager = get_game_manager()
    game = manager.get_game(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if game.status != "waiting":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game is already {game.status}",
        )

    success = manager.start_game(game_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to start game",
        )

    return {"message": "Game started", "game_id": game_id, "status": "in_progress"}


@router.post("/games/{game_id}/reset")
async def reset_game(game_id: str):
    """
    Reset a game to initial state.

    Args:
        game_id: Game UUID

    Returns:
        Success message
    """
    manager = get_game_manager()
    game = manager.get_game(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    success = manager.reset_game(game_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset game",
        )

    return {"message": "Game reset", "game_id": game_id, "status": "waiting"}


@router.delete("/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(game_id: str):
    """
    Delete a game and all associated data.

    Args:
        game_id: Game UUID
    """
    manager = get_game_manager()
    success = manager.delete_game(game_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )


@router.post("/games/{game_id}/throw")
async def manual_throw(game_id: str, throw_data: ThrowCreate):
    """
    Record a manual throw (used when camera detection fails).

    Args:
        game_id: Game UUID
        throw_data: Throw data (segment, multiplier)

    Returns:
        Throw result
    """
    manager = get_game_manager()
    game = manager.get_game(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if game.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game is not in progress (status: {game.status})",
        )

    throw_result = manager.process_throw(
        game_id=game_id,
        segment=throw_data.segment,
        multiplier=throw_data.multiplier,
    )

    if not throw_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid throw or turn already complete",
        )

    return {
        "message": "Throw recorded",
        "throw": {
            "player_id": throw_result.player_id,
            "player_name": throw_result.player_name,
            "segment": throw_result.segment,
            "multiplier": throw_result.multiplier,
            "total_score": throw_result.total_score,
            "segment_name": throw_result.segment_name,
            "remaining_score": throw_result.remaining_score,
            "is_bust": throw_result.is_bust,
            "throws_left": throw_result.throws_left,
            "throw_number": throw_result.throw_number,
        },
    }


@router.post("/games/{game_id}/undo")
async def undo_throw(game_id: str):
    """
    Undo the last throw.

    Args:
        game_id: Game UUID

    Returns:
        Success message
    """
    manager = get_game_manager()
    game = manager.get_game(game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    success = manager.undo_throw(game_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No throws to undo or game not in progress",
        )

    return {"message": "Last throw undone", "game_id": game_id}

@router.post("/player", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(player_name: str, db: AsyncSession = Depends(get_db)):
    """
    Create a new player.

    Args:
        player_name: Name of the player to create

    Returns:
        Player creation response with player_id
    """
    service = get_game_service()
    player = await service.create_player(db, player_name)

    return PlayerResponse(
        id=player.id,
        name=player.name,
        score=player.score,
        throws_this_turn=0,
        is_current=False,
    )


@router.get("/cameras")
async def get_camera_status():
    """
    Return active/inactive status for all configured cameras.

    Reads live state from the global CameraManager when available;
    falls back to a static inactive list if the manager has not yet started
    (e.g. OpenCV not installed on a dev machine).
    """
    # Lazy import to avoid a circular dependency: routes → main → routes.
    from main import camera_manager
    if camera_manager is not None:
        return {"cameras": camera_manager.get_camera_status()}
    # Fallback: camera manager not initialised (no OpenCV / dev mode).
    return {
        "cameras": [
            {"id": 0, "source": "0", "label": "Bal",   "active": False},
            {"id": 1, "source": "1", "label": "Jobb",  "active": False},
            {"id": 2, "source": "2", "label": "Felső", "active": False},
        ]
    }


@router.post("/cameras/sources")
async def set_camera_sources(
    source_0: str = "0",
    source_1: str = "1",
    source_2: str = "2",
):
    """
    Update camera sources at runtime and restart the camera manager.

    Each source is either a numeric device index ("0", "1", "2") for
    USB/built-in cameras, or an HTTP MJPEG URL for IP cameras
    (e.g. "http://192.168.1.100:8080/video" as served by the Android
    "IP Webcam" app).

    The detection loop is stopped, the manager restarted with new sources,
    and the loop resumed — all without restarting the FastAPI server.
    """
    # Lazy imports to avoid circular dependency.
    from main import camera_manager
    import camera.camera_loop as loop_module

    if camera_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera manager not initialised (OpenCV may not be available).",
        )

    await loop_module.stop()
    await camera_manager.stop()

    camera_manager.camera_ids = [source_0, source_1, source_2]

    await camera_manager.start()
    await loop_module.start()

    return {
        "message": "Camera sources updated",
        "sources": [source_0, source_1, source_2],
    }


@router.post("/cameras/board-config")
async def set_board_config(
    center_x_pct: float = 0.5,
    center_y_pct: float = 0.5,
    radius_pct: float = 0.4,
):
    """
    Update the board position used by mobile-camera dart detection.

    All values are fractions of frame dimensions (0.0 to 1.0).
    Changes take effect immediately for all subsequent frames.
    """
    if not (0.0 <= center_x_pct <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="center_x_pct must be in [0.0, 1.0]",
        )
    if not (0.0 <= center_y_pct <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="center_y_pct must be in [0.0, 1.0]",
        )
    if not (0.0 < radius_pct <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="radius_pct must be in (0.0, 1.0]",
        )
    _coordinate_mapper.update(center_x_pct, center_y_pct, radius_pct)
    return {
        "message": "Board config updated",
        "center_x_pct": center_x_pct,
        "center_y_pct": center_y_pct,
        "radius_pct": radius_pct,
    }


@router.get("/cameras/{camera_id}/snapshot")
async def camera_snapshot(
    camera_id: int,
    overlay: bool = Query(False, description="Draw debug overlay (contours, dart tip, stability)"),
    board: bool = Query(False, description="Draw configured board circle on the frame"),
):
    """
    Return the latest captured frame from a camera as a JPEG image.

    Open in a browser or use with curl:
        curl http://PI_IP:8000/api/cameras/0/snapshot --output frame.jpg
        curl "http://PI_IP:8000/api/cameras/0/snapshot?overlay=true" --output debug.jpg

    overlay=true draws:
      - Red contours (background subtraction result)
      - Yellow dot: last detected tip (not yet stable)
      - Green dot+ring: confirmed stable dart position
      - Stability counter in top-left corner

    board=true draws the configured board centre + radius circle in cyan.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise HTTPException(status_code=503, detail="OpenCV not available")

    from main import camera_manager
    if camera_manager is None or not camera_manager.running:
        raise HTTPException(status_code=503, detail="Camera manager not running")

    if camera_id >= len(camera_manager.cameras) or camera_id not in camera_manager.last_frames:
        raise HTTPException(status_code=404, detail=f"No frame available for camera {camera_id}")

    frame = camera_manager.last_frames[camera_id].copy()

    if overlay and camera_id < len(camera_manager.detectors):
        frame = camera_manager.detectors[camera_id].draw_debug(frame)

    if board and camera_id in camera_manager.frame_sizes:
        from api.websocket import _coordinate_mapper
        w, h = camera_manager.frame_sizes[camera_id]
        cx = int(_coordinate_mapper.center_x_pct * w)
        cy = int(_coordinate_mapper.center_y_pct * h)
        r  = int(_coordinate_mapper.radius_pct * min(w, h))
        cv2.circle(frame, (cx, cy), 5, (255, 255, 0), -1)   # cyan centre dot
        cv2.circle(frame, (cx, cy), r, (255, 255, 0), 2)    # cyan board circle

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode frame")

    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.post("/cameras/calibrate")
async def calibrate_cameras():
    """
    Trigger camera calibration (placeholder - will be implemented with camera integration).

    Returns:
        Calibration status
    """
    # TODO: Implement camera calibration
    return {
        "message": "Camera calibration not yet implemented",
        "status": "pending",
    }
