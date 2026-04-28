"""
WebSocket controller for PI Darts Counter.

Responsibility boundary
-----------------------
This module is a *controller* layer only.  It owns:
  - WebSocket connection lifecycle (connect / disconnect / cleanup)
  - Incoming message routing (type → handler)
  - Outgoing message construction and broadcast

It does NOT own:
  - Game business logic  → ThrowService / GameQueryService
  - Database persistence  → ThrowService (via AsyncSessionLocal sessions created here)
  - Dart detection math   → DartDetector / CoordinateMapper

DB session pattern
------------------
FastAPI's ``Depends(get_db)`` is not available inside the WebSocket message
loop, so each write operation opens its own session via ``AsyncSessionLocal``,
commits on success, and rolls back on any exception.  ThrowService never
commits or rolls back — the caller (this module) owns the transaction boundary.
"""
import base64
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from camera.coordinate_mapper import CoordinateMapper
from camera.detector import DartDetector
from database.db import AsyncSessionLocal
from game.game_manager import GameManager
from models.throw import ThrowResult
from services import GameQueryService, ThrowService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Per-game mobile-camera detector (one DartDetector per active game).
# Created on first camera_frame message, removed when the last client in the
# game's room disconnects.
_mobile_detectors: dict[str, DartDetector] = {}

# Shared CoordinateMapper — updated at runtime via POST /api/cameras/board-config.
_coordinate_mapper = CoordinateMapper()


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages WebSocket connections and per-game broadcast rooms."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(game_id, []).append(websocket)
        logger.info(
            "Client connected to game %s. Total connections: %d",
            game_id,
            len(self.active_connections[game_id]),
        )

    def disconnect(self, websocket: WebSocket, game_id: str) -> None:
        room = self.active_connections.get(game_id)
        if room and websocket in room:
            room.remove(websocket)
            logger.info(
                "Client disconnected from game %s. Remaining: %d",
                game_id,
                len(room),
            )
        if not self.active_connections.get(game_id):
            self.active_connections.pop(game_id, None)

    async def send_personal_message(
        self, message: dict[str, Any], websocket: WebSocket
    ) -> None:
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.error("Error sending personal message: %s", exc)

    async def broadcast(self, message: dict[str, Any], game_id: str) -> None:
        room = self.active_connections.get(game_id)
        if not room:
            return
        disconnected: list[WebSocket] = []
        for connection in room:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.error("Error broadcasting to connection: %s", exc)
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn, game_id)


# Global connection manager instance
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Pydantic message model
# ---------------------------------------------------------------------------

class WebSocketMessage(BaseModel):
    """Validated shape for every incoming WebSocket message."""
    type: str
    data: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Payload builders (pure — no I/O)
# ---------------------------------------------------------------------------

def _build_game_state_payload(game_id: str, query_svc: GameQueryService) -> dict[str, Any]:
    """
    Build the ``game_state`` payload dict from current in-memory state.

    Pure function: reads from ``query_svc`` (no DB, no I/O).  Used by both
    ``send_game_state`` (personal message on connect) and ``handle_undo_throw``
    (broadcast after undo).
    """
    game = query_svc.get_game(game_id)
    players = query_svc.get_players(game_id)
    current_player = query_svc.get_current_player(game_id)

    player_list = [
        {
            "id": p.id,
            "name": p.name,
            "score": p.score,
            "throwsThisTurn": p.throws_this_turn,
            "isCurrent": p.is_current,
        }
        for p in players
    ]

    return {
        "gameId": game.id if game else game_id,
        "mode": game.mode if game else None,
        "status": game.status if game else None,
        "round": game.round if game else 0,
        "players": player_list,
        "currentPlayerId": current_player.id if current_player else None,
        "lastThrow": None,
    }


def _compute_game_over_stats(game_id: str, query_svc: GameQueryService) -> dict[str, dict]:
    """
    Compute per-player end-of-game statistics.

    Bust throws are excluded from averages and highest-turn because they did
    not contribute to the player's score.  Throws are grouped into windows of
    3 to approximate "highest turn total".

    Returns a dict keyed by player name:
        {"avgPerDart": float, "highestTurn": int}
    """
    # Access throws_history directly from the underlying manager; GameQueryService
    # has no dedicated history accessor, and adding one is out of scope here.
    throws = query_svc._manager.throws_history.get(game_id, [])
    players = query_svc.get_players(game_id)
    stats: dict[str, dict] = {}

    for player in players:
        valid_throws = [t for t in throws if t.player_id == player.id and not t.is_bust]
        num_darts = len(valid_throws)
        total_scored = sum(t.total_score for t in valid_throws)
        avg_per_dart = round(total_scored / num_darts, 1) if num_darts > 0 else 0.0

        turn_totals = [
            sum(t.total_score for t in valid_throws[i : i + 3])
            for i in range(0, len(valid_throws), 3)
        ]
        stats[player.name] = {
            "avgPerDart": avg_per_dart,
            "highestTurn": max(turn_totals) if turn_totals else 0,
        }

    return stats


# ---------------------------------------------------------------------------
# Broadcast helpers
# ---------------------------------------------------------------------------

async def _broadcast_throw_result(
    game_id: str,
    throw_result: ThrowResult,
    query_svc: GameQueryService,
) -> None:
    """
    Broadcast the appropriate WebSocket message(s) for a completed throw.

    Handles all three outcomes:
      - Bust  → ``bust`` message only
      - Normal throw  → ``throw_detected``, optionally ``turn_complete``
      - Winning throw → ``throw_detected`` + ``game_over``

    Called by both ``handle_manual_score`` and ``handle_camera_frame`` so
    that broadcast logic is never duplicated.
    """
    if throw_result.is_bust:
        next_player = query_svc.get_current_player(game_id)
        await manager.broadcast(
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

    # Normal (non-bust) throw -------------------------------------------------
    await manager.broadcast(
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

    # Turn complete (throws_left == -1 signals the manager advanced the turn) --
    # Only emit when the game is NOT over; a winning throw is handled below.
    if throw_result.throws_left == -1 and throw_result.remaining_score != 0:
        next_player = query_svc.get_current_player(game_id)
        last_turn = query_svc.get_last_turn_throws(game_id)
        turn_total = sum(t.total_score for t in last_turn)
        await manager.broadcast(
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

    # Game over ---------------------------------------------------------------
    if throw_result.remaining_score == 0:
        game = query_svc.get_game(game_id)
        stats = _compute_game_over_stats(game_id, query_svc)
        await manager.broadcast(
            {
                "type": "game_over",
                "data": {
                    "winnerId": throw_result.player_id,
                    "winnerName": throw_result.player_name,
                    "finalThrow": throw_result.segment_name,
                    "totalRounds": game.round if game else 0,
                    "stats": stats,
                },
            },
            game_id,
        )


# ---------------------------------------------------------------------------
# Per-connection state sender (called once on connect)
# ---------------------------------------------------------------------------

async def send_game_state(
    websocket: WebSocket,
    game_id: str,
    query_svc: GameQueryService,
) -> None:
    """Send the full game state snapshot to a single newly-connected client."""
    game = query_svc.get_game(game_id)
    if not game:
        await manager.send_personal_message(
            {
                "type": "error",
                "data": {
                    "code": "GAME_NOT_FOUND",
                    "message": f"Game {game_id} not found",
                    "severity": "critical",
                },
            },
            websocket,
        )
        return

    payload = _build_game_state_payload(game_id, query_svc)
    await manager.send_personal_message(
        {"type": "game_state", "data": payload},
        websocket,
    )


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------

async def handle_manual_score(
    game_id: str,
    data: dict[str, Any],
    throw_svc: ThrowService,
    query_svc: GameQueryService,
) -> None:
    """
    Handle a ``manual_score`` message from the client.

    Validates the incoming segment/multiplier, delegates to ThrowService
    (which persists the throw atomically), then broadcasts the result.
    """
    segment = data.get("segment")
    multiplier = data.get("multiplier")

    if segment is None or multiplier is None:
        await manager.broadcast(
            {
                "type": "error",
                "data": {
                    "code": "INVALID_INPUT",
                    "message": "Missing segment or multiplier",
                    "severity": "warning",
                },
            },
            game_id,
        )
        return

    async with AsyncSessionLocal() as db:
        try:
            throw_result = await throw_svc.process_throw(db, game_id, segment, multiplier)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("handle_manual_score: DB error for game %s: %s", game_id, exc)
            await manager.broadcast(
                {
                    "type": "error",
                    "data": {
                        "code": "PROCESSING_ERROR",
                        "message": str(exc),
                        "severity": "warning",
                    },
                },
                game_id,
            )
            return

    if throw_result is None:
        await manager.broadcast(
            {
                "type": "error",
                "data": {
                    "code": "INVALID_THROW",
                    "message": "Invalid throw or turn already complete",
                    "severity": "warning",
                },
            },
            game_id,
        )
        return

    await _broadcast_throw_result(game_id, throw_result, query_svc)


async def handle_undo_throw(
    game_id: str,
    throw_svc: ThrowService,
    query_svc: GameQueryService,
) -> None:
    """
    Handle an ``undo_throw`` message from the client.

    Rolls back the last throw in both memory and the database, then broadcasts
    the updated full game state so all clients resync.
    """
    async with AsyncSessionLocal() as db:
        try:
            success = await throw_svc.undo_throw(db, game_id)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("handle_undo_throw: DB error for game %s: %s", game_id, exc)
            await manager.broadcast(
                {
                    "type": "error",
                    "data": {
                        "code": "PROCESSING_ERROR",
                        "message": str(exc),
                        "severity": "warning",
                    },
                },
                game_id,
            )
            return

    if success:
        payload = _build_game_state_payload(game_id, query_svc)
        await manager.broadcast({"type": "game_state", "data": payload}, game_id)
    else:
        await manager.broadcast(
            {
                "type": "error",
                "data": {
                    "code": "UNDO_FAILED",
                    "message": "No throws to undo or game not in progress",
                    "severity": "warning",
                },
            },
            game_id,
        )


async def handle_next_turn(game_id: str, query_svc: GameQueryService) -> None:
    """
    Handle a ``next_turn`` message from the client.

    Force-advances to the next player even if the current turn is not
    complete.  Useful when a player wants to concede their remaining throws.

    Note: ThrowService has no ``next_turn`` method; the advance is done directly
    via the underlying GameManager.  A future ThrowService.next_turn() method
    should be added if this operation needs DB persistence (e.g. recording
    a forfeit turn).
    """
    game = query_svc.get_game(game_id)
    if not game or game.status != "in_progress":
        await manager.broadcast(
            {
                "type": "error",
                "data": {
                    "code": "INVALID_STATE",
                    "message": "Game is not in progress",
                    "severity": "warning",
                },
            },
            game_id,
        )
        return

    current_player = query_svc.get_current_player(game_id)
    if current_player:
        # Access the manager directly — this is intentionally not routed
        # through ThrowService until a persistence requirement is added.
        query_svc._manager._next_player(game_id)

    next_player = query_svc.get_current_player(game_id)
    await manager.broadcast(
        {
            "type": "turn_complete",
            "data": {
                "playerId": current_player.id if current_player else None,
                "throws": [],
                "turnTotal": 0,
                "nextPlayerId": next_player.id if next_player else None,
            },
        },
        game_id,
    )


async def handle_camera_frame(
    game_id: str,
    data: dict[str, Any],
    throw_svc: ThrowService,
    query_svc: GameQueryService,
) -> None:
    """
    Process a JPEG frame sent by the mobile camera.

    Decodes the base64-encoded frame, runs the DartDetector stability
    pipeline, and — once a stable position is confirmed — maps it to a
    dartboard segment and processes the throw through the same path as
    ``handle_manual_score`` (ThrowService → _broadcast_throw_result).

    No-op when:
    - OpenCV is not installed (Windows dev machines without cv2).
    - The frame payload is missing or corrupt.
    - The game does not exist or is not in progress.
    - The dart position has not yet stabilised.
    - The dart lands outside the board (segment == 0, i.e. a miss).
    """
    # Guard: cv2 is absent on Windows dev machines — skip silently.
    try:
        import cv2
        import numpy as np
    except ImportError:
        return

    frame_b64: str | None = data.get("frame")
    if not frame_b64:
        return

    game = query_svc.get_game(game_id)
    if not game or game.status != "in_progress":
        return

    # Decode base64 JPEG → BGR numpy array ------------------------------------
    try:
        frame_bytes = base64.b64decode(frame_b64)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return
    except Exception as exc:
        logger.warning("camera_frame decode error for game %s: %s", game_id, exc)
        return

    # Build or reuse the per-game DartDetector --------------------------------
    from config import settings  # local import: config may not be loaded at module init

    stability_threshold = max(5, int(1.5 * settings.mobile_camera_fps))
    if game_id not in _mobile_detectors:
        _mobile_detectors[game_id] = DartDetector(stability_threshold=stability_threshold)
    detector = _mobile_detectors[game_id]

    # Run the MOG2 detection pipeline -----------------------------------------
    # Synchronous call is acceptable at the ≤10 fps mobile frame rate; the
    # latency impact is small enough that run_in_executor is not warranted.
    position = detector.process_frame(frame)
    if position is None:
        return  # dart not yet stable

    # Map stable pixel position → dartboard segment ---------------------------
    h, w = frame.shape[:2]
    segment, multiplier = _coordinate_mapper.pixel_to_segment(position[0], position[1], w, h)

    if segment == 0:
        logger.debug(
            "Mobile camera: dart outside board (miss) for game %s — resetting detector.",
            game_id,
        )
        detector.reset()
        return

    logger.info(
        "Mobile camera: dart at segment=%d multiplier=%d (game=%s)",
        segment,
        multiplier,
        game_id,
    )
    detector.reset()

    # Process throw through service (identical path to handle_manual_score) ---
    async with AsyncSessionLocal() as db:
        try:
            throw_result = await throw_svc.process_throw(db, game_id, segment, multiplier)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(
                "handle_camera_frame: DB error for game %s: %s", game_id, exc
            )
            return

    if throw_result is None:
        return

    await _broadcast_throw_result(game_id, throw_result, query_svc)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

async def websocket_endpoint(websocket: WebSocket, game_id: str) -> None:
    """
    Main WebSocket endpoint.

    Creates fresh ``GameQueryService`` and ``ThrowService`` instances per
    connection (no shared mutable state — both services are thin wrappers
    around the GameManager singleton and the DB layer).  Sends the full game
    state on connect, then routes incoming messages to the appropriate handler
    until the client disconnects.
    """
    manager_instance = GameManager.get_instance()
    query_svc = GameQueryService(manager_instance)
    throw_svc = ThrowService(manager_instance)

    await manager.connect(websocket, game_id)

    try:
        await send_game_state(websocket, game_id, query_svc)

        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON from client (game=%s): %s", game_id, exc)
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "data": {
                            "code": "INVALID_JSON",
                            "message": "Invalid JSON format",
                            "severity": "warning",
                        },
                    },
                    websocket,
                )
                continue

            msg_type: str | None = message.get("type")
            msg_data: dict[str, Any] = message.get("data") or {}

            if msg_type == "manual_score":
                await handle_manual_score(game_id, msg_data, throw_svc, query_svc)
            elif msg_type == "undo_throw":
                await handle_undo_throw(game_id, throw_svc, query_svc)
            elif msg_type == "next_turn":
                await handle_next_turn(game_id, query_svc)
            elif msg_type == "camera_frame":
                await handle_camera_frame(game_id, msg_data, throw_svc, query_svc)
            else:
                logger.warning("Unknown message type '%s' (game=%s)", msg_type, game_id)
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "data": {
                            "code": "UNKNOWN_MESSAGE_TYPE",
                            "message": f"Unknown message type: {msg_type}",
                            "severity": "info",
                        },
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected from game %s", game_id)
    except Exception as exc:
        logger.error("Unexpected WebSocket error (game=%s): %s", game_id, exc)
    finally:
        manager.disconnect(websocket, game_id)
        # Release the per-game mobile detector only when the last client for
        # this game room has gone.  Multiple clients may share one room.
        if game_id not in manager.active_connections:
            _mobile_detectors.pop(game_id, None)
