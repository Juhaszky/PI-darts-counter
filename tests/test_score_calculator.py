"""
Unit tests for game/score_calculator.py — specifically calculate_throw().

Each test exercises one distinct scenario described in the task spec plus
a handful of boundary cases to ensure correctness on edge inputs.
"""
import pytest

from game.score_calculator import calculate_throw
from models import ThrowResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PLAYER_ID = "player-uuid-001"
PLAYER_NAME = "Alice"


def make_throw(
    segment: int,
    multiplier: int,
    current_score: int,
    throw_number: int = 1,
    throws_left: int = 2,
    double_out: bool = False,
) -> ThrowResult:
    """Thin wrapper that calls calculate_throw with default player identity."""
    return calculate_throw(
        segment=segment,
        multiplier=multiplier,
        current_score=current_score,
        player_id=PLAYER_ID,
        player_name=PLAYER_NAME,
        throw_number=throw_number,
        throws_left=throws_left,
        double_out=double_out,
    )


# ---------------------------------------------------------------------------
# Normal single throw
# ---------------------------------------------------------------------------

class TestNormalThrow:
    def test_single_20_from_501(self):
        result = make_throw(segment=20, multiplier=1, current_score=501)

        assert result.total_score == 20
        assert result.remaining_score == 481
        assert result.is_bust is False
        # remaining_score > 0 confirms this is not a winning throw
        assert result.remaining_score != 0
        assert result.segment_name == "20"

    def test_player_identity_preserved(self):
        result = make_throw(segment=5, multiplier=1, current_score=100)

        assert result.player_id == PLAYER_ID
        assert result.player_name == PLAYER_NAME

    def test_throw_number_preserved(self):
        result = make_throw(segment=10, multiplier=1, current_score=200, throw_number=2)

        assert result.throw_number == 2


# ---------------------------------------------------------------------------
# Triple (×3)
# ---------------------------------------------------------------------------

class TestTripleThrow:
    def test_triple_20_from_501(self):
        result = make_throw(segment=20, multiplier=3, current_score=501)

        assert result.total_score == 60
        assert result.remaining_score == 441
        assert result.is_bust is False
        assert result.segment_name == "T20"

    def test_triple_1_segment_name(self):
        result = make_throw(segment=1, multiplier=3, current_score=100)
        assert result.segment_name == "T1"


# ---------------------------------------------------------------------------
# Double (×2) — winner path
# ---------------------------------------------------------------------------

class TestDoubleThrowWinner:
    def test_double_16_finishes_game(self):
        # 32 remaining, throw D16 → remaining=0, winner (not bust)
        # ThrowResult has no is_winner field; a win is remaining_score==0 + not bust.
        result = make_throw(segment=16, multiplier=2, current_score=32)

        assert result.total_score == 32
        assert result.remaining_score == 0
        assert result.is_bust is False
        assert result.segment_name == "D16"


# ---------------------------------------------------------------------------
# Bust — negative score
# ---------------------------------------------------------------------------

class TestBustNegativeScore:
    def test_triple_20_from_50_busts(self):
        # 50 - 60 = -10 → bust, score restored
        result = make_throw(segment=20, multiplier=3, current_score=50)

        assert result.is_bust is True
        assert result.remaining_score == 50  # restored to current_score

    def test_bust_total_score_still_computed(self):
        # Even on a bust, total_score records the attempted value
        result = make_throw(segment=20, multiplier=3, current_score=50)
        assert result.total_score == 60


# ---------------------------------------------------------------------------
# Bust — score becomes exactly 1
# ---------------------------------------------------------------------------

class TestBustScoreOne:
    def test_single_1_from_2_busts(self):
        # 2 - 1 = 1 → bust (cannot finish on 1)
        result = make_throw(segment=1, multiplier=1, current_score=2)

        assert result.is_bust is True
        assert result.remaining_score == 2  # restored

    def test_single_19_from_20_busts_at_one(self):
        # 20 - 19 = 1 → bust
        result = make_throw(segment=19, multiplier=1, current_score=20)
        assert result.is_bust is True


# ---------------------------------------------------------------------------
# Double-out win
# ---------------------------------------------------------------------------

class TestDoubleOutWin:
    def test_double_16_wins_with_double_out(self):
        # D16 reaches exactly 0 and is a double → valid win (not bust).
        # ThrowResult has no is_winner field; win = remaining_score==0 + not bust.
        result = make_throw(
            segment=16, multiplier=2, current_score=32, double_out=True
        )

        assert result.remaining_score == 0
        assert result.is_bust is False

    def test_bullseye_wins_with_double_out(self):
        # Bullseye (50) is an accepted double-out finish.
        result = make_throw(
            segment=50, multiplier=1, current_score=50, double_out=True
        )

        assert result.remaining_score == 0
        assert result.is_bust is False


# ---------------------------------------------------------------------------
# Double-out bust (single throw, not a double)
# ---------------------------------------------------------------------------

class TestDoubleOutBust:
    def test_single_16_from_16_busts_with_double_out(self):
        # Would reach 0 but finishing throw is single, not double → bust.
        # Score must be restored; is_bust=True confirms the throw was rejected.
        result = make_throw(
            segment=16, multiplier=1, current_score=16, double_out=True
        )

        assert result.is_bust is True
        assert result.remaining_score == 16  # restored

    def test_triple_from_remaining_busts_with_double_out(self):
        result = make_throw(
            segment=20, multiplier=3, current_score=60, double_out=True
        )

        assert result.is_bust is True
        assert result.remaining_score == 60


# ---------------------------------------------------------------------------
# Third throw signal (throws_left → -1)
# ---------------------------------------------------------------------------

class TestThirdThrowSignal:
    def test_third_throw_non_bust_sets_throws_left_minus_one(self):
        # throw_number=3, throws_left=0 → result.throws_left should be -1
        result = make_throw(
            segment=10,
            multiplier=1,
            current_score=200,
            throw_number=3,
            throws_left=0,
        )

        assert result.throws_left == -1

    def test_third_throw_bust_sets_throws_left_zero(self):
        # On bust the implementation forces throws_left=0 regardless
        result = make_throw(
            segment=20,
            multiplier=3,
            current_score=10,  # 10 - 60 = -50 → bust
            throw_number=3,
            throws_left=0,
        )

        assert result.is_bust is True
        assert result.throws_left == 0


# ---------------------------------------------------------------------------
# Segment name formatting — Bull and Bullseye
# ---------------------------------------------------------------------------

class TestSegmentNames:
    def test_bull_25_segment_name(self):
        result = make_throw(segment=25, multiplier=1, current_score=100)
        assert result.segment_name == "BULL"

    def test_bullseye_50_segment_name(self):
        result = make_throw(segment=50, multiplier=1, current_score=100)
        assert result.segment_name == "BULLSEYE"

    def test_single_segment_has_no_prefix(self):
        result = make_throw(segment=5, multiplier=1, current_score=100)
        assert result.segment_name == "5"

    def test_double_prefix(self):
        result = make_throw(segment=8, multiplier=2, current_score=100)
        assert result.segment_name == "D8"

    def test_triple_prefix(self):
        result = make_throw(segment=19, multiplier=3, current_score=100)
        assert result.segment_name == "T19"


# ---------------------------------------------------------------------------
# throws_left decrement (non-bust)
# ---------------------------------------------------------------------------

class TestThrowsLeftDecrement:
    def test_throws_left_decremented_by_one_on_normal_throw(self):
        result = make_throw(
            segment=10, multiplier=1, current_score=200, throws_left=2
        )
        # throws_left passed in = 2, result should be 1
        assert result.throws_left == 1

    def test_throws_left_zero_after_second_throw(self):
        result = make_throw(
            segment=10, multiplier=1, current_score=200, throws_left=1
        )
        assert result.throws_left == 0
