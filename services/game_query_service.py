"""
Read-only query service over in-memory game state.

This module contains GameQueryService, the single place where controllers
that need to *read* game state import from. It has no async methods, no
database access, and no mutations — making it safe to call from any context
without holding a database session or an asyncio lock.
"""

from typing import Optional

from game.game_manager import GameManager
from models.game import Game
from models.player import Player
from models.throw import ThrowResult


class GameQueryService:
    """
    Read-only view over in-memory game state.

    All methods read from GameManager without touching the database.
    This service has no async methods and never mutates state — it is
    safe to call from anywhere without holding a DB session or lock.

    Callers that only need to inspect game state should depend on this
    service rather than on GameManager directly, so they remain decoupled
    from throw-processing and lifecycle concerns (Interface Segregation).
    """

    def __init__(self, game_manager: GameManager) -> None:
        """
        Initialise the service with an injected GameManager.

        Args:
            game_manager: The shared in-memory game state manager.
        """
        self._manager = game_manager

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def get_game(self, game_id: str) -> Optional[Game]:
        """
        Return the Game model for *game_id*, or None if not found.

        Args:
            game_id: UUID string identifying the game.

        Returns:
            The Game Pydantic model if the game exists in memory, else None.
        """
        return self._manager.get_game(game_id)

    def get_players(self, game_id: str) -> list[Player]:
        """
        Return all players for *game_id* ordered by their turn position.

        Players are stored in turn order (order_idx 0, 1, 2 …) so the
        returned list preserves that order without additional sorting.

        Args:
            game_id: UUID string identifying the game.

        Returns:
            List of Player models in turn order; empty list if the game
            does not exist in memory.
        """
        return self._manager.get_players(game_id)

    def get_current_player(self, game_id: str) -> Optional[Player]:
        """
        Return the Player whose turn it currently is.

        Delegates to GameManager which resolves the current player via
        ``game.current_player_idx``.

        Args:
            game_id: UUID string identifying the game.

        Returns:
            The active Player model, or None if the game does not exist
            or has no players yet.
        """
        return self._manager.get_current_player(game_id)

    def get_last_turn_throws(self, game_id: str) -> list[ThrowResult]:
        """
        Return throws from the last *completed* turn.

        GameManager populates ``last_turn_throws`` when a turn ends
        (either all 3 throws used, or a bust) and clears it on game reset.
        This snapshot is used primarily for the ``turn_complete`` WebSocket
        broadcast.

        A shallow copy is returned so callers cannot accidentally mutate
        manager-owned state.

        Args:
            game_id: UUID string identifying the game.

        Returns:
            List of ThrowResult models from the last completed turn; empty
            list if no turn has been completed yet or the game does not exist.
        """
        raw: list[ThrowResult] = self._manager.last_turn_throws.get(game_id, [])
        return list(raw)

    def game_exists(self, game_id: str) -> bool:
        """
        Return True if *game_id* is currently tracked in memory.

        A game is present in memory from the moment it is created until it
        is explicitly deleted via the lifecycle service.

        Args:
            game_id: UUID string identifying the game.

        Returns:
            True if the game exists in memory, False otherwise.
        """
        return self._manager.get_game(game_id) is not None

    def is_in_progress(self, game_id: str) -> bool:
        """
        Return True if the game exists and its status is ``'in_progress'``.

        Convenience predicate used by controllers to gate throw submission
        and other actions that require an active game session.

        Args:
            game_id: UUID string identifying the game.

        Returns:
            True if the game is found and its status equals ``'in_progress'``,
            False in all other cases (not found, waiting, or finished).
        """
        game: Optional[Game] = self._manager.get_game(game_id)
        return game is not None and game.status == "in_progress"
