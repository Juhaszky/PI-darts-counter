"""
Throw data models for PI Darts Counter.
"""
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ThrowBase(BaseModel):
    """Base throw model."""
    segment: Annotated[int, Field(ge=0, le=60)]  # 0-20, 25 (bull), 50 (bullseye)
    multiplier: Annotated[int, Field(ge=1, le=3)]  # 1 (single), 2 (double), 3 (triple)


class ThrowCreate(ThrowBase):
    """Request model for manual throw."""
    pass


class ThrowResult(ThrowBase):
    """Complete throw result after calculation."""
    player_id: str
    player_name: str
    total_score: int  # segment × multiplier
    segment_name: str  # "T20", "D16", "BULL", "BULLSEYE"
    remaining_score: int
    is_bust: bool
    throws_left: int
    throw_number: Annotated[int, Field(ge=1, le=3)]

    @staticmethod
    def format_segment_name(segment: int, multiplier: int) -> str:
        """Format segment name for display (e.g., T20, D16, BULL)."""
        if segment == 50:
            return "BULLSEYE"
        if segment == 25:
            return "BULL"

        prefix = ""
        if multiplier == 3:
            prefix = "T"
        elif multiplier == 2:
            prefix = "D"

        return f"{prefix}{segment}"


class Throw(ThrowBase):
    """Stored throw model (for database)."""
    id: str  # UUID
    game_id: str
    player_id: str
    round: int
    throw_num: Annotated[int, Field(ge=1, le=3)]
    total: int
    is_bust: bool
    timestamp: datetime

    model_config = {"from_attributes": True}


class ThrowResponse(BaseModel):
    """Response model for throw data sent to client."""
    segment_name: str
    total: int

    model_config = {"from_attributes": True}
