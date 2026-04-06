"""
Player data models for PI Darts Counter.
"""
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class PlayerBase(BaseModel):
    """Base player model for creation."""
    name: Annotated[str, Field(min_length=1, max_length=50)]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Trim whitespace from name."""
        return v.strip()


class Player(PlayerBase):
    """Complete player model with game state."""
    id: str  # UUID
    game_id: str  # UUID
    score: int
    order_idx: int
    throws_this_turn: int = 0
    is_current: bool = False

    model_config = {"from_attributes": True}


class PlayerCreate(PlayerBase):
    """Request model for adding a player."""
    pass


class PlayerResponse(BaseModel):
    """Response model for player data sent to client."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    id: str
    name: str
    score: int
    throws_this_turn: int
    is_current: bool
