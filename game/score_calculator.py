"""
Score calculation logic for PI Darts Counter.
Handles throw result calculation based on segment, multiplier, and current score.
"""
from models import ThrowResult


def calculate_throw(
    segment: int,
    multiplier: int,
    current_score: int,
    player_id: str,
    player_name: str,
    throw_number: int,
    throws_left: int,
    double_out: bool = False,
) -> ThrowResult:
    """
    Calculate the result of a throw.

    Args:
        segment: Segment value (0-20, 25 for bull, 50 for bullseye)
        multiplier: 1 (single), 2 (double), 3 (triple)
        current_score: Player's current score before this throw
        player_id: UUID of the player
        player_name: Name of the player
        throw_number: Current throw number (1-3)
        throws_left: Remaining throws after this one
        double_out: Whether double-out rule is enabled

    Returns:
        ThrowResult with calculated scores and flags
    """
    total_score = segment * multiplier
    new_score = current_score - total_score

    # Bust conditions:
    # 1. Score goes negative
    # 2. Score becomes exactly 1 (cannot finish on 1)
    # 3. Double-out enabled and finishing throw is not a double (multiplier != 2)
    is_bust = new_score < 0 or new_score == 1

    # Check for winner (score reaches exactly 0)
    is_winner = new_score == 0

    # If double-out is enabled, winner must finish with double or bullseye
    if double_out and is_winner and multiplier != 2 and segment != 50:
        is_bust = True
        is_winner = False

    # If bust, restore score to current
    remaining_score = current_score if is_bust else new_score

    segment_name = ThrowResult.format_segment_name(segment, multiplier)

    return ThrowResult(
        player_id=player_id,
        player_name=player_name,
        segment=segment,
        multiplier=multiplier,
        total_score=total_score,
        segment_name=segment_name,
        remaining_score=remaining_score,
        is_bust=is_bust,
        throws_left=throws_left - 1 if not is_bust else 0,
        throw_number=throw_number,
    )


def calculate_segment_score(segment: int, multiplier: int) -> int:
    """
    Simple helper to calculate total score for a segment.

    Args:
        segment: Segment value (0-20, 25, 50)
        multiplier: 1, 2, or 3

    Returns:
        Total score (segment × multiplier)
    """
    return segment * multiplier
