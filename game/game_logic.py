"""
Game logic module for PI Darts Counter.
Implements 301 and 501 game rules.
"""
from typing import Literal
from models import GameMode


def get_starting_score(mode: GameMode) -> int:
    """
    Get the starting score for a game mode.

    Args:
        mode: Game mode ("301" or "501")

    Returns:
        Starting score integer
    """
    if mode == "301":
        return 301
    elif mode == "501":
        return 501
    else:
        raise ValueError(f"Unknown game mode: {mode}")


def is_valid_finish_score(score: int) -> bool:
    """
    Check if a score is a valid finishing score.
    Valid finish scores are 2-170 (must be able to finish in one dart).

    Args:
        score: Remaining score to check

    Returns:
        True if the score can potentially be finished in one dart
    """
    # Cannot finish if score is 0 (already finished), 1 (impossible), or > 170 (max is T20 + T20 + bullseye in 3 darts, but one dart max is 60)
    # Actually, maximum one-dart checkout is 50 (bullseye) or 40 (D20)
    # But for game logic, we check if score is theoretically reachable
    if score <= 0 or score == 1:
        return False
    return True


def is_bust(new_score: int, double_out: bool, multiplier: int, segment: int) -> bool:
    """
    Determine if a throw results in a bust.

    Args:
        new_score: Score after the throw
        double_out: Whether double-out rule is enabled
        multiplier: Multiplier of the throw
        segment: Segment value of the throw

    Returns:
        True if bust, False otherwise
    """
    # Bust if score goes negative
    if new_score < 0:
        return True

    # Bust if score becomes exactly 1 (cannot finish on 1)
    if new_score == 1:
        return True

    # If score is 0 and double-out is enabled, must be a double or bullseye
    if new_score == 0 and double_out:
        if multiplier != 2 and segment != 50:
            return True

    return False


def check_winner(score: int) -> bool:
    """
    Check if a player has won (score is exactly 0).

    Args:
        score: Player's current score

    Returns:
        True if player has won
    """
    return score == 0


def validate_throw(segment: int, multiplier: int) -> bool:
    """
    Validate that a throw has valid segment and multiplier values.

    Args:
        segment: Segment value (0-20, 25, 50)
        multiplier: Multiplier (1, 2, 3)

    Returns:
        True if valid, False otherwise
    """
    # Valid segments: 0 (miss), 1-20, 25 (bull), 50 (bullseye)
    valid_segments = list(range(0, 21)) + [25, 50]
    if segment not in valid_segments:
        return False

    # Valid multipliers: 1, 2, 3
    if multiplier not in [1, 2, 3]:
        return False

    # Special cases:
    # - 25 (bull) can only be single (multiplier 1)
    # - 50 (bullseye) can only be single (multiplier 1)
    # - 0 (miss) can only be single (multiplier 1)
    if segment in [0, 25, 50] and multiplier != 1:
        return False

    return True


def calculate_average_per_dart(total_score: int, num_darts: int) -> float:
    """
    Calculate average score per dart.

    Args:
        total_score: Total score accumulated
        num_darts: Number of darts thrown

    Returns:
        Average score per dart
    """
    if num_darts == 0:
        return 0.0
    return round(total_score / num_darts, 2)
