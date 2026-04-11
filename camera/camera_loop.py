"""
Background camera detection loop for PI Darts Counter.

Runs continuously as an asyncio Task, reads frames from all cameras,
detects a stable dart position, maps it to a dartboard segment via
CoordinateMapper, and auto-processes throws for the currently active game.

Usage (from main.py startup):
    from camera import camera_loop
    camera_loop.setup(camera_manager, coordinate_mapper)
    await camera_loop.start()

Shutdown (from main.py shutdown):
    await camera_loop.stop()
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from camera.camera_manager import CameraManager
    from camera.coordinate_mapper import CoordinateMapper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state — set once from main.py via setup(), never mutated again
# until the next setup() call.
# ---------------------------------------------------------------------------

_camera_manager: "CameraManager | None" = None
_coordinate_mapper: "CoordinateMapper | None" = None
_loop_task: asyncio.Task | None = None
_running: bool = False

_FRAME_INTERVAL: float = 1.0 / 30  # 30 fps target


def setup(camera_manager: "CameraManager", coordinate_mapper: "CoordinateMapper") -> None:
    """
    Inject dependencies.  Called once from main.py after startup so that this
    module never imports from main.py (avoids circular imports).
    """
    global _camera_manager, _coordinate_mapper
    _camera_manager = camera_manager
    _coordinate_mapper = coordinate_mapper
    logger.debug("camera_loop: dependencies injected.")


async def start() -> None:
    """Start the background detection loop as an asyncio Task."""
    global _loop_task, _running
    if _running:
        logger.debug("camera_loop.start() called but loop is already running — no-op.")
        return
    _running = True
    _loop_task = asyncio.create_task(_detection_loop(), name="camera_detection_loop")
    logger.info("Camera detection loop started.")


async def stop() -> None:
    """Cancel the background detection loop and await its completion."""
    global _loop_task, _running
    _running = False
    if _loop_task and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    _loop_task = None
    logger.info("Camera detection loop stopped.")


# ---------------------------------------------------------------------------
# Internal loop
# ---------------------------------------------------------------------------

async def _detection_loop() -> None:
    """
    Main frame-capture and throw-detection loop.

    Each iteration:
    1. Captures one frame from every active camera (offloaded to thread executor
       inside CameraManager.capture_frames so the event loop is not blocked).
    2. Asks the manager for the first confirmed-stable dart position.
    3. If a position is found, maps it to a board segment via CoordinateMapper.
    4. Finds the currently active in_progress game.
    5. Calls GameManager.process_throw() and broadcasts the result.
    6. Resets all detectors so the next dart can be detected cleanly.

    Errors in a single iteration are caught and logged; the loop always
    continues after a short back-off to prevent a single bad frame from
    crashing the entire session.
    """
    # Deferred imports to avoid circular-import problems at module load time.
    from game import GameManager
    from api.websocket import manager as ws_manager

    while _running:
        try:
            if _camera_manager is None or not _camera_manager.running:
                await asyncio.sleep(0.5)
                continue

            # Capture frames concurrently across all cameras.
            # The method returns a list of frames but we only need it to trigger
            # the internal DartDetector.process_frame() calls as a side-effect.
            await _camera_manager.capture_frames()

            # Check whether any detector has reached a confirmed stable position.
            result = _camera_manager.get_dart_position()
            if result is None:
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            x, y, frame_w, frame_h = result

            # Map pixel coordinates to a dartboard segment.
            if _coordinate_mapper is None:
                logger.warning("camera_loop: coordinate_mapper not set — dart ignored.")
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            segment, multiplier = _coordinate_mapper.pixel_to_segment(x, y, frame_w, frame_h)
            logger.info(
                "Dart detected: pixel=(%.1f, %.1f) → segment=%d multiplier=%d",
                x, y, segment, multiplier,
            )

            # Reset all detectors immediately so the same dart is not scored twice
            # even if a game or active-game check below bails out.
            for det in _camera_manager.detectors:
                det.reset()

            if segment == 0:
                # Dart landed outside the board — not a scoring throw.
                logger.debug("Dart is a miss (outside board) — skipping.")
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            # Find the first in_progress game.
            game_manager = GameManager.get_instance()
            active_game_id = _find_active_game(game_manager)
            if active_game_id is None:
                logger.debug("No active game — dart detection ignored.")
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            # Process throw through the game engine.
            throw_result = game_manager.process_throw(active_game_id, segment, multiplier)
            if throw_result is None:
                logger.warning(
                    "process_throw returned None for game %s (segment=%d, multiplier=%d)",
                    active_game_id, segment, multiplier,
                )
                await asyncio.sleep(_FRAME_INTERVAL)
                continue

            # Broadcast the result to all connected WebSocket clients.
            await _broadcast_throw(ws_manager, active_game_id, throw_result, game_manager)

        except asyncio.CancelledError:
            # Propagate cancellation so stop() can await cleanly.
            raise
        except Exception as exc:
            logger.error("Camera detection loop error: %s", exc, exc_info=True)
            # Back-off after an unexpected error to avoid a tight error loop.
            await asyncio.sleep(1.0)


def _find_active_game(game_manager) -> str | None:
    """Return the game_id of the first in_progress game, or None."""
    for game_id, game in game_manager.games.items():
        if game.status == "in_progress":
            return game_id
    return None


async def _broadcast_throw(ws_manager, game_id: str, throw_result, game_manager) -> None:
    """
    Broadcast throw result events to all WebSocket clients in the game room.

    Emits:
    - ``bust``          — if the throw caused a bust
    - ``throw_detected`` — for every valid throw
    - ``turn_complete``  — after the 3rd throw of a turn (throws_left sentinel == -1)
    - ``game_over``      — when remaining_score reaches exactly 0
    """
    if throw_result.is_bust:
        next_player = game_manager.get_current_player(game_id)
        await ws_manager.broadcast(
            {
                "type": "bust",
                "data": {
                    "playerId": throw_result.player_id,
                    "playerName": throw_result.player_name,
                    "scoreBefore": throw_result.remaining_score,
                    "attemptedThrow": throw_result.total_score,
                    "scoreRestored": throw_result.remaining_score,
                    "nextPlayerId": next_player.id if next_player else None,
                },
            },
            game_id,
        )
        return

    await ws_manager.broadcast(
        {
            "type": "throw_detected",
            "data": {
                "playerId": throw_result.player_id,
                "playerName": throw_result.player_name,
                "segment": throw_result.segment,
                "multiplier": throw_result.multiplier,
                "totalScore": throw_result.total_score,
                "segmentName": throw_result.segment_name,
                "remainingScore": throw_result.remaining_score,
                "isBust": False,
                "throwsLeft": throw_result.throws_left,
                "throwNumber": throw_result.throw_number,
            },
        },
        game_id,
    )

    # throws_left == -1 is the sentinel GameManager uses to signal that the
    # 3rd throw of a turn has just been processed and _next_player() was called.
    if throw_result.throws_left == -1 and throw_result.remaining_score != 0:
        next_player = game_manager.get_current_player(game_id)
        last_turn = game_manager.last_turn_throws.get(game_id, [])
        turn_total = sum(t.total_score for t in last_turn)
        await ws_manager.broadcast(
            {
                "type": "turn_complete",
                "data": {
                    "playerId": throw_result.player_id,
                    "throws": [
                        {"segmentName": t.segment_name, "total": t.total_score}
                        for t in last_turn
                    ],
                    "turnTotal": turn_total,
                    "nextPlayerId": next_player.id if next_player else None,
                },
            },
            game_id,
        )

    if throw_result.remaining_score == 0:
        game_obj = game_manager.get_game(game_id)
        throws = game_manager.throws_history.get(game_id, [])
        players_list = game_manager.get_players(game_id)
        stats: dict = {}
        for player in players_list:
            player_throws = [
                t for t in throws
                if t.player_id == player.id and not t.is_bust
            ]
            num_darts = len(player_throws)
            total_scored = sum(t.total_score for t in player_throws)
            avg_per_dart = round(total_scored / num_darts, 1) if num_darts > 0 else 0.0
            turn_totals = [
                sum(t.total_score for t in player_throws[i : i + 3])
                for i in range(0, len(player_throws), 3)
            ]
            stats[player.name] = {
                "avgPerDart": avg_per_dart,
                "highestTurn": max(turn_totals) if turn_totals else 0,
            }
        await ws_manager.broadcast(
            {
                "type": "game_over",
                "data": {
                    "winnerId": throw_result.player_id,
                    "winnerName": throw_result.player_name,
                    "finalThrow": throw_result.segment_name,
                    "totalRounds": game_obj.round if game_obj else 0,
                    "stats": stats,
                },
            },
            game_id,
        )
