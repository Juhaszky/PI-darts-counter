"""
Async repository functions for PI Darts Counter.

Each function accepts an AsyncSession as its first argument so the caller
controls transaction boundaries.  This makes the functions independently
testable and composable within a single database transaction.

Design decisions:
- `save_game` and `save_throw` use `merge()` (upsert by primary key).  This
  makes them idempotent — safe to call again after a crash-restart without
  duplicating rows.
- `finish_game` does a targeted UPDATE rather than a full object reload to
  avoid an unnecessary SELECT round-trip.
- Aggregate queries in `get_game_history` and `get_player_stats` run entirely
  in the database; no Python-level aggregation loops that would blow up on
  large history sets.
- Raw SQL strings are never used.  All queries go through the SQLAlchemy ORM
  or core expression language to ensure parameterisation.
- NO function in this module ever calls db.commit().  The caller (or get_db())
  is always responsible for committing or rolling back the session.
- db.flush() is used only where we need the DB to assign/return a generated
  value within the same transaction (e.g. after db.add() in create_player).
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy import delete, distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GameRecord, PlayerRecord, ThrowRecord
from models.game import Game
from models.player import Player
from models.throw import ThrowResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Game persistence
# ---------------------------------------------------------------------------

async def save_game(db: AsyncSession, game: Game, players: list[Player]) -> None:
    """
    Persist a game and its players to the database.

    Uses merge() so this is safe to call on both initial creation and on
    subsequent updates (e.g. status change after start/reset).

    Args:
        db:      Active async database session.
        game:    Pydantic Game model from the in-memory GameManager.
        players: Pydantic Player models belonging to this game.
    """
    game_record = GameRecord(
        id=game.id,
        mode=game.mode,
        status=game.status,
        double_out=int(game.double_out),
        winner_id=game.winner_id,
        created_at=game.created_at,
        finished_at=game.finished_at,
    )
    # merge() issues an INSERT or UPDATE based on whether the PK already exists.
    await db.merge(game_record)

    for player in players:
        player_record = PlayerRecord(
            id=player.id,
            game_id=player.game_id,
            name=player.name,
            score=player.score,
            order_idx=player.order_idx,
        )
        await db.merge(player_record)

    logger.debug("Saved game %s with %d players to database.", game.id, len(players))


async def finish_game(
    db: AsyncSession,
    game_id: str,
    winner_id: str,
    finished_at: datetime,
) -> None:
    """
    Mark a game as finished by updating its status, winner, and finish time.

    Issues a single UPDATE statement rather than loading the object first.

    Args:
        db:          Active async database session.
        game_id:     UUID string of the game to finish.
        winner_id:   UUID string of the winning player.
        finished_at: UTC datetime when the game ended.
    """
    stmt = (
        update(GameRecord)
        .where(GameRecord.id == game_id)
        .values(
            status="finished",
            winner_id=winner_id,
            finished_at=finished_at,
        )
    )
    await db.execute(stmt)
    logger.info("Game %s finished. Winner: %s.", game_id, winner_id)


async def get_game_by_id(db: AsyncSession, game_id: str) -> GameRecord | None:
    """
    Fetch a single game record by primary key.

    Args:
        db:      Active async database session.
        game_id: UUID string of the game to retrieve.

    Returns:
        The GameRecord if found, None otherwise.
    """
    stmt = select(GameRecord).where(GameRecord.id == game_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_game_status(db: AsyncSession, game_id: str, status: str) -> None:
    """
    Update the status field of an existing game record.

    Args:
        db:      Active async database session.
        game_id: UUID string of the game to update.
        status:  New status value ("waiting" | "in_progress" | "finished").
    """
    stmt = (
        update(GameRecord)
        .where(GameRecord.id == game_id)
        .values(status=status)
    )
    await db.execute(stmt)
    logger.debug("Updated game %s status to '%s'.", game_id, status)


async def delete_game(db: AsyncSession, game_id: str) -> None:
    """
    Delete a game record and all associated players and throws.

    Cascade deletes on the FK relationships handle players and throws
    automatically, so a single DELETE on games is sufficient.

    Args:
        db:      Active async database session.
        game_id: UUID string of the game to delete.
    """
    stmt = delete(GameRecord).where(GameRecord.id == game_id)
    await db.execute(stmt)
    logger.info("Deleted game %s (cascade removes players and throws).", game_id)


# ---------------------------------------------------------------------------
# Player persistence
# ---------------------------------------------------------------------------

async def get_players_by_game_id(
    db: AsyncSession, game_id: str
) -> list[PlayerRecord]:
    """
    Return all players for a game ordered by their turn position.

    Args:
        db:      Active async database session.
        game_id: UUID string of the parent game.

    Returns:
        List of PlayerRecord objects ordered by order_idx ascending.
    """
    stmt = (
        select(PlayerRecord)
        .where(PlayerRecord.game_id == game_id)
        .order_by(PlayerRecord.order_idx.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_player_score(
    db: AsyncSession, player_id: str, score: int
) -> None:
    """
    Update the persisted score for a single player.

    Args:
        db:        Active async database session.
        player_id: UUID string of the player to update.
        score:     New score value to write.
    """
    stmt = (
        update(PlayerRecord)
        .where(PlayerRecord.id == player_id)
        .values(score=score)
    )
    await db.execute(stmt)
    logger.debug("Updated player %s score to %d.", player_id, score)


async def reset_players_score(
    db: AsyncSession, game_id: str, starting_score: int
) -> None:
    """
    Reset every player in a game back to the starting score.

    Used by the reset_game operation to restore all player scores in a single
    UPDATE rather than one statement per player.

    Args:
        db:            Active async database session.
        game_id:       UUID string of the game whose players should be reset.
        starting_score: The mode's starting score (301 or 501).
    """
    stmt = (
        update(PlayerRecord)
        .where(PlayerRecord.game_id == game_id)
        .values(score=starting_score)
    )
    await db.execute(stmt)
    logger.debug(
        "Reset all players in game %s to score %d.", game_id, starting_score
    )


async def create_player(db: AsyncSession, name: str) -> PlayerRecord:
    """
    Insert a new, unassigned player row and return the persisted record.

    The player starts with no game association (game_id=None), score 0, and
    order_idx 0.  The caller is responsible for assigning game_id and
    order_idx before or after committing, as needed.

    Uses db.flush() — not db.commit() — so the insert becomes visible within
    the current transaction without ending it.  The caller controls the commit.

    Args:
        db:   Active async database session.
        name: Display name for the player (will be stripped of whitespace).

    Returns:
        Fully refreshed PlayerRecord with its generated id populated.
    """
    player = PlayerRecord(
        id=str(uuid.uuid4()),
        game_id=None,
        name=name.strip(),
        score=0,
        order_idx=0,
    )
    db.add(player)
    # flush() sends the INSERT to the DB within this transaction so that
    # db.refresh() can read the written state back without committing.
    await db.flush()
    await db.refresh(player)
    return player


# ---------------------------------------------------------------------------
# Throw persistence
# ---------------------------------------------------------------------------

async def save_throw(
    db: AsyncSession,
    game_id: str,
    throw: ThrowResult,
    round_num: int,
    throw_num: int,
) -> None:
    """
    Persist a single throw result to the database.

    A stable UUID is generated from the combination of game_id, player_id,
    round, and throw_num so that replaying the same throw (e.g. after a crash)
    produces the same PK and merge() becomes a no-op rather than a duplicate
    insert.

    Args:
        db:        Active async database session.
        game_id:   UUID string of the game this throw belongs to.
        throw:     Pydantic ThrowResult from the game engine.
        round_num: Current round number (1-indexed).
        throw_num: Throw number within the current turn (1-3).
    """
    # Deterministic UUID: the same logical throw always maps to the same DB row.
    throw_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_OID,
            f"{game_id}:{throw.player_id}:{round_num}:{throw_num}",
        )
    )

    throw_record = ThrowRecord(
        id=throw_id,
        game_id=game_id,
        player_id=throw.player_id,
        round=round_num,
        throw_num=throw_num,
        segment=throw.segment,
        multiplier=throw.multiplier,
        total=throw.total_score,
        is_bust=int(throw.is_bust),
        timestamp=datetime.utcnow(),
    )
    await db.merge(throw_record)

    logger.debug(
        "Saved throw game=%s player=%s round=%d throw=%d segment=%d mult=%d bust=%s.",
        game_id,
        throw.player_id,
        round_num,
        throw_num,
        throw.segment,
        throw.multiplier,
        throw.is_bust,
    )


async def delete_latest_throw(db: AsyncSession, game_id: str) -> bool:
    """
    Delete the most recently recorded throw for a game (undo support).

    Uses a two-step SELECT-then-DELETE by PK rather than a single
    DELETE ... ORDER BY ... LIMIT because SQLite's support for that syntax
    through the SQLAlchemy ORM is not guaranteed across driver versions.

    Args:
        db:      Active async database session.
        game_id: UUID string of the game whose latest throw should be removed.

    Returns:
        True if a throw was found and deleted, False if no throws exist.
    """
    # Step 1: find the PK of the most recent throw for this game.
    select_stmt = (
        select(ThrowRecord.id)
        .where(ThrowRecord.game_id == game_id)
        .order_by(ThrowRecord.timestamp.desc())
        .limit(1)
    )
    result = await db.execute(select_stmt)
    throw_id: str | None = result.scalar_one_or_none()

    if throw_id is None:
        logger.debug("delete_latest_throw: no throws found for game %s.", game_id)
        return False

    # Step 2: delete by PK — avoids any ambiguity if two throws share a
    # millisecond-precision timestamp.
    delete_stmt = delete(ThrowRecord).where(ThrowRecord.id == throw_id)
    await db.execute(delete_stmt)
    logger.debug("Deleted latest throw %s from game %s.", throw_id, game_id)
    return True


async def clear_game_throws(db: AsyncSession, game_id: str) -> None:
    """
    Delete every throw record that belongs to a game.

    Used by reset_game to wipe the throw history while keeping the game and
    player rows intact.

    Args:
        db:      Active async database session.
        game_id: UUID string of the game whose throws should be cleared.
    """
    stmt = delete(ThrowRecord).where(ThrowRecord.game_id == game_id)
    await db.execute(stmt)
    logger.debug("Cleared all throws for game %s.", game_id)


# ---------------------------------------------------------------------------
# Analytics / history queries
# ---------------------------------------------------------------------------

async def get_game_history(db: AsyncSession, limit: int = 10) -> list[dict]:
    """
    Return a summary of the most recently finished games.

    Each entry contains: game_id, mode, double_out, winner_id, created_at,
    finished_at, and total_throws (count of throws in that game).

    Args:
        db:    Active async database session.
        limit: Maximum number of records to return (default 10).

    Returns:
        List of dicts ordered by finished_at descending (most recent first).
    """
    stmt = (
        select(
            GameRecord.id,
            GameRecord.mode,
            GameRecord.double_out,
            GameRecord.winner_id,
            GameRecord.created_at,
            GameRecord.finished_at,
            func.count(ThrowRecord.id).label("total_throws"),
        )
        .outerjoin(ThrowRecord, ThrowRecord.game_id == GameRecord.id)
        .where(GameRecord.status == "finished")
        .group_by(GameRecord.id)
        .order_by(GameRecord.finished_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "game_id": row.id,
            "mode": row.mode,
            "double_out": bool(row.double_out),
            "winner_id": row.winner_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "total_throws": row.total_throws,
        }
        for row in rows
    ]


async def get_player_stats(db: AsyncSession, player_name: str) -> dict:
    """
    Return lifetime statistics for a player identified by name.

    Stats include: total games played, total wins, total throws, total score
    accumulated, average score per dart, and bust count.

    Note: player_name matching is case-sensitive. If the same physical person
    plays under slightly different names they will appear as separate entries.

    Args:
        db:          Active async database session.
        player_name: Exact player name string to look up.

    Returns:
        Dict with keys: player_name, games_played, wins, total_throws,
        total_score, avg_per_dart, busts.
    """
    # Aggregate throw-level stats directly from throws joined to players.
    stats_stmt = (
        select(
            func.count(ThrowRecord.id).label("total_throws"),
            func.sum(ThrowRecord.total).label("total_score"),
            func.sum(ThrowRecord.is_bust).label("busts"),
        )
        .join(PlayerRecord, PlayerRecord.id == ThrowRecord.player_id)
        .where(PlayerRecord.name == player_name)
    )
    stats_result = await db.execute(stats_stmt)
    stats_row = stats_result.one()

    # Count distinct games this player appeared in.
    games_stmt = (
        select(func.count(PlayerRecord.id.distinct()).label("games_played"))
        .where(PlayerRecord.name == player_name)
    )
    games_result = await db.execute(games_stmt)
    games_row = games_result.one()

    # Count wins: games where this player is the winner.
    wins_stmt = (
        select(func.count(GameRecord.id).label("wins"))
        .join(PlayerRecord, PlayerRecord.id == GameRecord.winner_id)
        .where(PlayerRecord.name == player_name)
    )
    wins_result = await db.execute(wins_stmt)
    wins_row = wins_result.one()

    total_throws: int = stats_row.total_throws or 0
    total_score: int = stats_row.total_score or 0
    busts: int = stats_row.busts or 0
    games_played: int = games_row.games_played or 0
    wins: int = wins_row.wins or 0

    avg_per_dart: float = (
        round(total_score / total_throws, 2) if total_throws > 0 else 0.0
    )

    return {
        "player_name": player_name,
        "games_played": games_played,
        "wins": wins,
        "total_throws": total_throws,
        "total_score": total_score,
        "avg_per_dart": avg_per_dart,
        "busts": busts,
    }


async def get_all_player_names(db: AsyncSession) -> list[str]:
    """
    Return a sorted, deduplicated list of every player name ever recorded.

    Useful for autocomplete on the player-creation screen.

    Args:
        db: Active async database session.

    Returns:
        List of unique player name strings, ordered alphabetically.
    """
    stmt = (
        select(distinct(PlayerRecord.name))
        .where(PlayerRecord.name.is_not(None))
        .order_by(PlayerRecord.name.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
