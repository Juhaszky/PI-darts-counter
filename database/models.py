"""
SQLAlchemy ORM models for PI Darts Counter.

These are the database-layer models (tables). They are intentionally kept
separate from the Pydantic models in models/ — the two layers must never bleed
into each other. Mapping between them happens in repository.py.

SQLite stores booleans as INTEGER (0/1); we reflect that in the Column types
so the schema is explicit rather than relying on driver coercion.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


class GameRecord(Base):
    """
    Persisted game record.

    `double_out` and any future boolean columns are stored as Integer (0/1)
    because SQLite has no native BOOLEAN type.
    """
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    mode: Mapped[str] = mapped_column(Text, nullable=False)          # "301" | "501"
    status: Mapped[str] = mapped_column(Text, nullable=False)        # "waiting" | "in_progress" | "finished"
    double_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0 | 1
    winner_id: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True, default=None)

    # Relationships (used by ORM joins, not loaded eagerly by default)
    players: Mapped[list["PlayerRecord"]] = relationship(
        "PlayerRecord",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="select",
    )
    throws: Mapped[list["ThrowRecord"]] = relationship(
        "ThrowRecord",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="select",
    )


class PlayerRecord(Base):
    """
    Persisted player record.

    `score` holds the player's score at the time the record was last written.
    For in-progress games this is the live score; for finished games it reflects
    the final state.
    """
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    game_id: Mapped[str] = mapped_column(
        Text, ForeignKey("games.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False)

    game: Mapped["GameRecord"] = relationship("GameRecord", back_populates="players")


class ThrowRecord(Base):
    """
    Persisted throw record.

    One row per individual dart throw. `is_bust` is stored as Integer (0/1).
    `throw_num` is 1-indexed within the turn (1, 2, or 3).
    `total` is the point value of this throw (segment × multiplier).
    """
    __tablename__ = "throws"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    game_id: Mapped[str] = mapped_column(
        Text, ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[str] = mapped_column(
        Text, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    throw_num: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-3 within turn
    segment: Mapped[int] = mapped_column(Integer, nullable=False)
    multiplier: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)      # segment × multiplier
    is_bust: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0 | 1
    timestamp: Mapped[datetime] = mapped_column(nullable=False)

    game: Mapped["GameRecord"] = relationship("GameRecord", back_populates="throws")
