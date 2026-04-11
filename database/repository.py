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
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GameRecord, PlayerRecord, ThrowRecord
from models.game import Game
from models.player import Player
from models.throw import ThrowResult

logger = logging.getLogger(__name__)


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
    # merge() issues an INSERT or UPDATE based on whether the PK already exists
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

    # The caller (or get_db()) is responsible for committing the session.
    logger.debug("Saved game %s with %d players to database.", game.id, len(players))


async def save_throw(
    db: AsyncSession,
    game_id: str,
    throw: ThrowResult,
    round_num: int,
    throw_num: int,
) -> None:
    """
    Persist a single throw result to the database.

    A stable UUID is generated from the combination of player_id, round, and
    throw_num so that replaying the same throw (e.g. after a crash) produces
    the same PK and merge() becomes a no-op rather than a duplicate insert.

    Args:
        db:        Active async database session.
        game_id:   UUID string of the game this throw belongs to.
        throw:     Pydantic ThrowResult from the game engine.
        round_num: Current round number (1-indexed).
        throw_num: Throw number within the current turn (1-3).
    """
    # Deterministic UUID: same throw always maps to the same DB row.
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

    avg_per_dart: float = round(total_score / total_throws, 2) if total_throws > 0 else 0.0

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
    stmt = (
        select(distinct(PlayerRecord.name))
        .where(PlayerRecord.name.is_not(None))
        .order_by(PlayerRecord.name.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def create_player(db: AsyncSession, name: str) -> PlayerRecord:
    player = PlayerRecord(
        id=str(uuid.uuid4()),
        game_id=None,   # only if this column is nullable; otherwise use a separate table
        name=name.strip(),
        score=0,
        order_idx=0,
    )
    db.add(player)
    await db.commit()
    await db.refresh(player)
    return player