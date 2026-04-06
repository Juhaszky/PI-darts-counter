"""
REST API routes for PI Darts Counter.
Handles game lifecycle, player management, and manual throw input.
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime

from models import (
    GameCreate,
    GameCreateResponse,
    GameResponse,
    PlayerResponse,
    ThrowCreate,
)
from game import GameManager

router = APIRouter(prefix="/api", tags=["games"])


def get_game_manager() -> GameManager:
    """Dependency to get GameManager singleton."""
    return GameManager.get_instance()


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


@router.get("/cameras")
async def get_camera_status():
    """
    Get camera status (placeholder - will be implemented with camera integration).

    Returns:
        Camera status for all cameras
    """
    # TODO: Implement actual camera status checking
    return {
        "cameras": [
            {"id": 0, "label": "Bal", "active": False},
            {"id": 1, "label": "Jobb", "active": False},
            {"id": 2, "label": "Felső", "active": False},
        ]
    }


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
