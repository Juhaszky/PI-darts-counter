"""
Database layer for PI Darts Counter.

Public API:
    init_db      — create all tables on startup (call once from lifespan event)
    get_db       — FastAPI async dependency that yields an AsyncSession
    save_game    — upsert a game + its players
    save_throw   — persist a single throw result
    finish_game  — mark a game as finished with winner + timestamp
"""
from database.db import get_db, init_db
from database.repository import finish_game, save_game, save_throw

__all__ = [
    "init_db",
    "get_db",
    "save_game",
    "save_throw",
    "finish_game",
]
