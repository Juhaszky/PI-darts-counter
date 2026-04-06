"""
Game data models for PI Darts Counter.
"""
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from datetime import datetime
from models.player import PlayerCreate, PlayerResponse


GameMode = Literal["301", "501"]
GameStatus = Literal["waiting", "in_progress", "finished"]


class GameBase(BaseModel):
    """Base game model."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    mode: GameMode
    double_out: bool = False


class GameCreate(GameBase):
    """Request model for creating a new game."""
    players: Annotated[list[PlayerCreate], Field(min_length=2, max_length=4)]


class Game(GameBase):
    """Complete game model with state."""
    id: str  # UUID
    status: GameStatus
    round: int = 1
    current_player_idx: int = 0
    winner_id: str | None = None
    created_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class GameState(BaseModel):
    """Complete game state for WebSocket broadcast."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    game_id: str
    mode: GameMode
    status: GameStatus
    round: int
    players: list[PlayerResponse]
    current_player_id: str
    last_throw: dict | None = None  # Will be ThrowResult serialized


class GameCreateResponse(BaseModel):
    """Response after creating a game."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    game_id: str
    mode: GameMode
    status: GameStatus
    created_at: datetime


class GameResponse(BaseModel):
    """Response model for GET /api/games/{game_id}."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    game_id: str
    mode: GameMode
    status: GameStatus
    round: int
    double_out: bool
    players: list[PlayerResponse]
    current_player_id: str | None = None
    winner_id: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
