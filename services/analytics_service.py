"""
Analytics service for PI Darts Counter.

Provides read-only analytical queries over persisted game data.
This module has no dependency on GameManager or any mutable in-memory state —
all data comes exclusively from the database via repository functions.

Design:
- Single Responsibility: only analytical/historical reads, never writes.
- Open/Closed: new stat types (leaderboard, per-game averages, streaks) are
  added as new methods without touching existing ones.
- Interface Segregation: analytics routes import only AnalyticsService; they
  have no knowledge of ThrowService, LifecycleService, or GameManager.
- Dependency Inversion: delegates all DB access to repository functions, which
  could be swapped for a Protocol-backed mock in tests without touching this
  class.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from database import repository as repo

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Provides read-only analytical queries over persisted game data.

    All methods are DB-bound (require an active session) and read-only.
    No GameManager dependency — analytics work from the historical DB
    record, not the live in-memory state.
    """

    async def get_game_history(
        self, db: AsyncSession, limit: int = 10
    ) -> list[dict]:
        """
        Return a summary of the most recently finished games.

        Each entry: game_id, mode, double_out, winner_id, created_at,
        finished_at, total_throws. Ordered by finished_at DESC.

        Args:
            db:    Active async database session.
            limit: Maximum number of records to return. Must be >= 1.

        Returns:
            List of game summary dicts, most recent first.

        Raises:
            ValueError: If limit is less than 1.
        """
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit!r}")

        logger.debug("Fetching game history (limit=%d).", limit)
        history = await repo.get_game_history(db, limit=limit)
        logger.info("Returned %d game history records.", len(history))
        return history

    async def get_player_stats(
        self, db: AsyncSession, player_name: str
    ) -> dict:
        """
        Return lifetime stats for a player by exact name.

        Keys: player_name, games_played, wins, total_throws,
        total_score, avg_per_dart, busts.
        Note: name matching is case-sensitive.

        Args:
            db:          Active async database session.
            player_name: Exact, case-sensitive player name to look up.

        Returns:
            Dict of lifetime statistics for the given player.

        Raises:
            ValueError: If player_name is blank.
            LookupError: If no games have been recorded under this name.
        """
        player_name = player_name.strip()
        if not player_name:
            raise ValueError("player_name must not be blank.")

        logger.debug("Fetching stats for player %r.", player_name)
        stats = await repo.get_player_stats(db, player_name=player_name)

        # The repository always returns a zeroed dict for unknown names.
        # Treat zero games_played as "player not found" so callers can
        # distinguish a genuinely unknown name from a player with real data.
        if stats["games_played"] == 0:
            logger.warning("No records found for player %r.", player_name)
            raise LookupError(
                f"No game records found for player {player_name!r}. "
                "Name matching is case-sensitive."
            )

        logger.info(
            "Stats for player %r: %d games, %d wins, %.2f avg/dart.",
            player_name,
            stats["games_played"],
            stats["wins"],
            stats["avg_per_dart"],
        )
        return stats

    async def get_all_player_names(self, db: AsyncSession) -> list[str]:
        """
        Return all distinct player names stored in the DB, alphabetically sorted.

        Args:
            db: Active async database session.

        Returns:
            Sorted list of unique player name strings. Empty list when no
            players have been recorded yet.
        """
        logger.debug("Fetching all distinct player names.")
        names = await repo.get_all_player_names(db)
        logger.debug("Found %d distinct player name(s).", len(names))
        return names
