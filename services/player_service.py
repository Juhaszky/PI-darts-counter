"""
Service layer for standalone player creation.

PlayerService handles the single responsibility of persisting a new player
record that is not yet associated with any game.  It is intentionally narrow:
no GameManager dependency, no throw logic, no game lifecycle involvement.

Transaction ownership
---------------------
``create_player`` accepts ``db: AsyncSession`` from the caller.  The caller
(route handler) owns commit/rollback.  This service never calls
``db.commit()`` or ``db.rollback()``.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from database import repository as repo
from database.models import PlayerRecord

logger = logging.getLogger(__name__)


class PlayerService:
    """
    Manages player persistence operations.

    Players can be created standalone (before a game) or are created
    implicitly when a game is created (via GameManager.create_game).
    This service handles the standalone creation path only.

    No GameManager dependency — standalone player creation is purely a
    DB operation without in-memory game state involvement.
    """

    async def create_player(self, db: AsyncSession, name: str) -> PlayerRecord:
        """
        Create a new player record in the database.

        The player starts unassigned (game_id=None) with score 0.
        Name is whitespace-stripped by the repository.

        Args:
            db:   Active async session. Caller owns commit/rollback.
            name: Display name (1-50 chars, validated by Pydantic at the route level).

        Returns:
            The freshly inserted and refreshed PlayerRecord ORM object.
        """
        player = await repo.create_player(db, name)
        logger.info("Created standalone player '%s' (id=%s).", player.name, player.id)
        return player
