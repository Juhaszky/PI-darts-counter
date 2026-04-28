"""
GameLifecycleService — game state transition management.

Single Responsibility: owns only the four lifecycle state transitions
(create → start → reset / delete).  Throw processing, undo, player
management, and analytics are deliberately out of scope so that future
game-mode extensions only touch this file.

Transaction ownership
---------------------
Every state-changing method accepts ``db: AsyncSession`` as its first
argument.  The caller (route handler) owns the transaction: ``get_db()``
auto-commits on a clean return and rolls back on any unhandled exception.
This service never calls ``db.commit()`` or ``db.rollback()``.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database import repository as repo
from game.game_logic import get_starting_score
from game.game_manager import GameManager
from models.game import Game, GameCreate
from models.player import Player

logger = logging.getLogger(__name__)


class GameLifecycleService:
    """
    Manages game state transitions.

    Each method applies the mutation to in-memory state via GameManager,
    then persists the change to the DB within the caller's transaction.
    The caller (route handler) owns commit/rollback — this service never
    calls db.commit() or db.rollback().

    Accepts a GameManager instance so the service is independently
    testable without starting the singleton.  In production, inject via
    ``GameManager.get_instance()``.
    """

    def __init__(self, game_manager: GameManager) -> None:
        self._manager = game_manager

    async def create_game(
        self,
        db: AsyncSession,
        game_data: GameCreate,
    ) -> tuple[Game, list[Player]]:
        """
        Create a new game in memory and persist it to the database.

        Delegates creation to GameManager (which assigns UUIDs and initial
        player scores), then writes the resulting game and player rows via
        ``repo.save_game``.  The two operations are not atomic at the
        Python level, but share the caller's DB session so they will be
        committed or rolled back together.

        Args:
            db:        Active async database session (caller owns transaction).
            game_data: Validated creation payload (mode, double_out, players).

        Returns:
            A tuple of (Game, list[Player]) reflecting the freshly created
            in-memory state.
        """
        game, players = self._manager.create_game(game_data)
        await repo.save_game(db, game, players)
        logger.info(
            "Created game %s (mode=%s, players=%d, double_out=%s).",
            game.id,
            game.mode,
            len(players),
            game.double_out,
        )
        return game, players

    async def start_game(self, db: AsyncSession, game_id: str) -> bool:
        """
        Transition a game from ``waiting`` to ``in_progress``.

        Idempotent at the HTTP level: if the game is already ``in_progress``
        the manager returns False and the DB write is skipped, so no
        spurious status update is issued.

        Args:
            db:      Active async database session (caller owns transaction).
            game_id: UUID string of the game to start.

        Returns:
            True if the transition succeeded, False if the game was not
            found or was not in the ``waiting`` state.
        """
        success = self._manager.start_game(game_id)
        if success:
            await repo.update_game_status(db, game_id, "in_progress")
            logger.info("Game %s started.", game_id)
        else:
            logger.warning(
                "start_game: game %s not found or not in 'waiting' state.", game_id
            )
        return success

    async def reset_game(self, db: AsyncSession, game_id: str) -> bool:
        """
        Reset a game to its initial ``waiting`` state.

        Clears all throw history and restores every player's score to the
        mode's starting value (301 or 501).  The game and player rows are
        kept in the database — only status, winner, scores, and throw
        history change.

        ``game.mode`` is read *before* calling ``manager.reset_game()`` to
        ensure the starting score is computed from the authoritative
        pre-reset value.  Although the manager does not clear the game
        object, making this explicit guards against future refactors.

        DB writes are ordered to match the logical reset sequence:
          1. Clear throw history (removes FK-dependent rows first).
          2. Restore player scores.
          3. Update game status to ``waiting``.

        Args:
            db:      Active async database session (caller owns transaction).
            game_id: UUID string of the game to reset.

        Returns:
            True if the reset succeeded, False if the game was not found.
        """
        game: Optional[Game] = self._manager.get_game(game_id)
        if game is None:
            logger.warning("reset_game: game %s not found.", game_id)
            return False

        # Capture mode and derive starting_score BEFORE the manager mutates
        # the game object so the DB writes use the correct value even if a
        # future refactor changes when reset_game() clears game state.
        starting_score: int = get_starting_score(game.mode)
        game_mode: str = game.mode  # for log message only

        success = self._manager.reset_game(game_id)
        if success:
            await repo.clear_game_throws(db, game_id)
            await repo.reset_players_score(db, game_id, starting_score)
            await repo.update_game_status(db, game_id, "waiting")
            logger.info(
                "Game %s reset (mode=%s, starting_score=%d).",
                game_id,
                game_mode,
                starting_score,
            )
        return success

    async def delete_game(self, db: AsyncSession, game_id: str) -> bool:
        """
        Delete a game from both in-memory state and the database.

        In-memory deletion happens first so that any concurrent request that
        arrives between the two operations finds the game already gone and
        fails fast.  The DB delete cascades to players and throws via FK
        constraints, so a single DELETE on the games table is sufficient.

        Args:
            db:      Active async database session (caller owns transaction).
            game_id: UUID string of the game to delete.

        Returns:
            True if the game existed and was deleted, False if not found.
        """
        in_memory_deleted = self._manager.delete_game(game_id)
        if in_memory_deleted:
            await repo.delete_game(db, game_id)
            logger.info("Game %s deleted.", game_id)
        else:
            logger.warning("delete_game: game %s not found in memory.", game_id)
        return in_memory_deleted
