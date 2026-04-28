"""
REST API routes for PI Darts Counter.

This module is a thin controller layer. It is responsible exclusively for:
  - Parsing and validating HTTP requests (handled by FastAPI + Pydantic).
  - Delegating ALL business operations to the appropriate service.
  - Shaping HTTP responses and selecting appropriate status codes.

No game logic, score calculation, or direct database queries belong here.
Camera endpoints are exempt: they read hardware state directly and have no
business-logic equivalent in any service.

Services follow the Interface Segregation Principle — each route declares only
the service(s) it actually uses.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from services import (
    GameQueryService,
    GameLifecycleService,
    ThrowService,
    PlayerService,
    AnalyticsService,
    get_query_service,
    get_lifecycle_service,
    get_throw_service,
    get_player_service,
    get_analytics_service,
)
from database.db import get_db
from api.websocket import _coordinate_mapper

router = APIRouter(prefix="/api", tags=["games"])


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "PI Darts Counter API",
    }


# ---------------------------------------------------------------------------
# Game lifecycle
# ---------------------------------------------------------------------------

@router.post("/games", response_model=GameCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    game_data: GameCreate,
    db: AsyncSession = Depends(get_db),
    lifecycle: GameLifecycleService = Depends(get_lifecycle_service),
):
    """
    Create a new game with players.

    Args:
        game_data: Game creation data with mode, double_out, and players.

    Returns:
        Game creation response with game_id.
    """
    game, _players = await lifecycle.create_game(db, game_data)
    return GameCreateResponse(
        game_id=game.id,
        mode=game.mode,
        status=game.status,
        created_at=game.created_at,
    )


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: str,
    query: GameQueryService = Depends(get_query_service),
):
    """
    Get game state by ID.

    Read-only — no database session needed; all state is in memory.

    Args:
        game_id: Game UUID.

    Returns:
        Complete game state including all players and current turn info.
    """
    game = query.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    players = query.get_players(game_id)
    current_player = query.get_current_player(game_id)

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
async def start_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    query: GameQueryService = Depends(get_query_service),
    lifecycle: GameLifecycleService = Depends(get_lifecycle_service),
):
    """
    Start a game (transition from waiting to in_progress).

    Returns 400 if the game is not in the 'waiting' state so that callers
    receive a clear message rather than a silent no-op.

    Args:
        game_id: Game UUID.

    Returns:
        Success message with new status.
    """
    game = query.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if game.status != "waiting":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game is already {game.status}",
        )

    success = await lifecycle.start_game(db, game_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to start game",
        )

    return {"message": "Game started", "game_id": game_id, "status": "in_progress"}


@router.post("/games/{game_id}/reset")
async def reset_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    query: GameQueryService = Depends(get_query_service),
    lifecycle: GameLifecycleService = Depends(get_lifecycle_service),
):
    """
    Reset a game to its initial waiting state.

    Args:
        game_id: Game UUID.

    Returns:
        Success message with restored status.
    """
    game = query.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    success = await lifecycle.reset_game(db, game_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reset game",
        )

    return {"message": "Game reset", "game_id": game_id, "status": "waiting"}


@router.delete("/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle: GameLifecycleService = Depends(get_lifecycle_service),
):
    """
    Delete a game and all associated data.

    No pre-flight query needed — lifecycle.delete_game() returns False when the
    game does not exist, which maps directly to 404.

    Args:
        game_id: Game UUID.
    """
    success = await lifecycle.delete_game(db, game_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    # Return an explicit empty response; FastAPI does not suppress the body
    # automatically for 204 when the route function returns a value.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Throw management
# ---------------------------------------------------------------------------

@router.post("/games/{game_id}/throw")
async def manual_throw(
    game_id: str,
    throw_data: ThrowCreate,
    db: AsyncSession = Depends(get_db),
    query: GameQueryService = Depends(get_query_service),
    throw_svc: ThrowService = Depends(get_throw_service),
):
    """
    Record a manual throw (used when camera detection fails).

    Args:
        game_id:    Game UUID.
        throw_data: Throw data (segment, multiplier).

    Returns:
        Throw result including remaining score, bust flag, and throws left.
    """
    game = query.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    if game.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game is not in progress (status: {game.status})",
        )

    throw_result = await throw_svc.process_throw(
        db,
        game_id,
        throw_data.segment,
        throw_data.multiplier,
    )
    if throw_result is None:
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
async def undo_throw(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    query: GameQueryService = Depends(get_query_service),
    throw_svc: ThrowService = Depends(get_throw_service),
):
    """
    Undo the last recorded throw for the current player.

    Args:
        game_id: Game UUID.

    Returns:
        Success message.
    """
    game = query.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    success = await throw_svc.undo_throw(db, game_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No throws to undo or game not in progress",
        )

    return {"message": "Last throw undone", "game_id": game_id}


# ---------------------------------------------------------------------------
# Player management
# ---------------------------------------------------------------------------

@router.post("/player", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(
    player_name: str,
    db: AsyncSession = Depends(get_db),
    player_svc: PlayerService = Depends(get_player_service),
):
    """
    Create a new player record (unassigned to any game).

    Args:
        player_name: Display name for the player.

    Returns:
        Player response with id and name.
    """
    player_record = await player_svc.create_player(db, player_name)
    return PlayerResponse(
        id=player_record.id,
        name=player_record.name,
        score=player_record.score,
        throws_this_turn=0,
        is_current=False,
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/history")
async def get_game_history(
    limit: int = Query(10, ge=1, le=100, description="Max number of finished games to return"),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """
    Return a summary of the most recently finished games.

    Each entry contains: game_id, mode, double_out, winner_id,
    created_at, finished_at, total_throws. Ordered newest first.
    """
    return await analytics.get_game_history(db, limit=limit)


@router.get("/players")
async def get_all_player_names(
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Return all distinct player names stored in the database, alphabetically sorted."""
    names = await analytics.get_all_player_names(db)
    return {"players": names}


@router.get("/players/{player_name}/stats")
async def get_player_stats(
    player_name: str,
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """
    Return lifetime statistics for a player by exact name.

    Stats include: games_played, wins, total_throws, total_score,
    avg_per_dart, busts. Name matching is case-sensitive.
    """
    try:
        return await analytics.get_player_stats(db, player_name)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ---------------------------------------------------------------------------
# Camera endpoints — read hardware state directly; no service involvement
# ---------------------------------------------------------------------------

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
        Calibration status.
    """
    # TODO: Implement camera calibration
    return {
        "message": "Camera calibration not yet implemented",
        "status": "pending",
    }
