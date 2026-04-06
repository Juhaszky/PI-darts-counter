"""
WebSocket API for PI Darts Counter.
Handles real-time communication with mobile clients.
"""
import json
import logging
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from models import PlayerResponse
from game import GameManager

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}  # game_id -> list of WebSocket

    async def connect(self, websocket: WebSocket, game_id: str):
        """
        Accept a new WebSocket connection and add to game room.

        Args:
            websocket: WebSocket connection
            game_id: Game UUID
        """
        await websocket.accept()

        if game_id not in self.active_connections:
            self.active_connections[game_id] = []

        self.active_connections[game_id].append(websocket)
        logger.info(f"Client connected to game {game_id}. Total connections: {len(self.active_connections[game_id])}")

    def disconnect(self, websocket: WebSocket, game_id: str):
        """
        Remove a WebSocket connection from game room.

        Args:
            websocket: WebSocket connection
            game_id: Game UUID
        """
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
                logger.info(f"Client disconnected from game {game_id}. Remaining connections: {len(self.active_connections[game_id])}")

            # Clean up empty game rooms
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific client.

        Args:
            message: Message dict to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict[str, Any], game_id: str):
        """
        Broadcast a message to all clients in a game room.

        Args:
            message: Message dict to broadcast
            game_id: Game UUID
        """
        if game_id not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[game_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn, game_id)


# Global connection manager instance
manager = ConnectionManager()


class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""
    type: str
    data: dict[str, Any] | None = None


async def send_game_state(websocket: WebSocket, game_id: str):
    """
    Send complete game state to a client (typically on connect).

    Args:
        websocket: WebSocket connection
        game_id: Game UUID
    """
    game_manager = GameManager.get_instance()
    game = game_manager.get_game(game_id)

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

    players = game_manager.get_players(game_id)
    current_player = game_manager.get_current_player(game_id)

    player_responses = [
        {
            "id": p.id,
            "name": p.name,
            "score": p.score,
            "throwsThisTurn": p.throws_this_turn,
            "isCurrent": p.is_current,
        }
        for p in players
    ]

    await manager.send_personal_message(
        {
            "type": "game_state",
            "data": {
                "gameId": game.id,
                "mode": game.mode,
                "status": game.status,
                "round": game.round,
                "players": player_responses,
                "currentPlayerId": current_player.id if current_player else None,
                "lastThrow": None,
            },
        },
        websocket,
    )


async def handle_manual_score(game_id: str, data: dict[str, Any]):
    """
    Handle manual score input from client.

    Args:
        game_id: Game UUID
        data: Message data containing segment and multiplier
    """
    try:
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

        game_manager = GameManager.get_instance()
        throw_result = game_manager.process_throw(game_id, segment, multiplier)

        if not throw_result:
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

        # Broadcast throw result
        if throw_result.is_bust:
            await manager.broadcast(
                {
                    "type": "bust",
                    "data": {
                        "playerId": throw_result.player_id,
                        "playerName": throw_result.player_name,
                        "scoreBefore": throw_result.remaining_score,
                        "attemptedThrow": throw_result.total_score,
                        "scoreRestored": throw_result.remaining_score,
                    },
                },
                game_id,
            )
        else:
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
                        "isBust": throw_result.is_bust,
                        "throwsLeft": throw_result.throws_left,
                        "throwNumber": throw_result.throw_number,
                    },
                },
                game_id,
            )

            # Check for winner
            if throw_result.remaining_score == 0:
                game = game_manager.get_game(game_id)
                await manager.broadcast(
                    {
                        "type": "game_over",
                        "data": {
                            "winnerId": throw_result.player_id,
                            "winnerName": throw_result.player_name,
                            "finalThrow": throw_result.segment_name,
                            "totalRounds": game.round if game else 0,
                            "stats": {},  # TODO: Calculate detailed stats
                        },
                    },
                    game_id,
                )

    except Exception as e:
        logger.error(f"Error handling manual score: {e}")
        await manager.broadcast(
            {
                "type": "error",
                "data": {
                    "code": "PROCESSING_ERROR",
                    "message": str(e),
                    "severity": "warning",
                },
            },
            game_id,
        )


async def handle_undo_throw(game_id: str):
    """
    Handle undo throw request from client.

    Args:
        game_id: Game UUID
    """
    game_manager = GameManager.get_instance()
    success = game_manager.undo_throw(game_id)

    if success:
        # Broadcast updated game state after undo
        game = game_manager.get_game(game_id)
        players = game_manager.get_players(game_id)
        current_player = game_manager.get_current_player(game_id)

        if game:
            await manager.broadcast(
                {
                    "type": "game_state",
                    "data": {
                        "gameId": game.id,
                        "mode": game.mode,
                        "status": game.status,
                        "round": game.round,
                        "players": [
                            {
                                "id": p.id,
                                "name": p.name,
                                "score": p.score,
                                "throwsThisTurn": p.throws_this_turn,
                                "isCurrent": p.is_current,
                            }
                            for p in players
                        ],
                        "currentPlayerId": current_player.id if current_player else None,
                        "lastThrow": None,
                    },
                },
                game_id,
            )
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


async def handle_next_turn(game_id: str):
    """
    Handle manual next turn request from client.

    Args:
        game_id: Game UUID
    """
    game_manager = GameManager.get_instance()
    game = game_manager.get_game(game_id)

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

    # Force move to next player (even if current turn not complete)
    current_player = game_manager.get_current_player(game_id)
    if current_player:
        game_manager._next_player(game_id)

        next_player = game_manager.get_current_player(game_id)
        await manager.broadcast(
            {
                "type": "turn_complete",
                "data": {
                    "playerId": current_player.id,
                    "throws": [],  # TODO: Include actual turn throws
                    "turnTotal": 0,  # TODO: Calculate turn total
                    "nextPlayerId": next_player.id if next_player else None,
                },
            },
            game_id,
        )


async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """
    WebSocket endpoint handler.

    Args:
        websocket: WebSocket connection
        game_id: Game UUID
    """
    await manager.connect(websocket, game_id)

    try:
        # Send initial game state
        await send_game_state(websocket, game_id)

        # Message loop
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")
                msg_data = message.get("data", {})

                if msg_type == "manual_score":
                    await handle_manual_score(game_id, msg_data)
                elif msg_type == "undo_throw":
                    await handle_undo_throw(game_id)
                elif msg_type == "next_turn":
                    await handle_next_turn(game_id)
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
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

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
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

    except WebSocketDisconnect:
        manager.disconnect(websocket, game_id)
        logger.info(f"Client disconnected from game {game_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, game_id)
