"""
Unit tests for game/game_logic.py.

Covers:
- get_starting_score
- validate_throw
- is_bust
- check_winner
- calculate_average_per_dart
"""
import pytest

from game.game_logic import (
    calculate_average_per_dart,
    check_winner,
    get_starting_score,
    is_bust,
    validate_throw,
)


# ---------------------------------------------------------------------------
# get_starting_score
# ---------------------------------------------------------------------------

class TestGetStartingScore:
    def test_mode_301_returns_301(self):
        assert get_starting_score("301") == 301

    def test_mode_501_returns_501(self):
        assert get_starting_score("501") == 501

    def test_invalid_mode_raises_value_error(self):
        with pytest.raises(ValueError):
            get_starting_score("201")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            get_starting_score("")

    def test_numeric_type_raises_value_error(self):
        # The function signature accepts GameMode (str), passing an int
        # that is not a recognised literal must raise ValueError.
        with pytest.raises((ValueError, TypeError)):
            get_starting_score(501)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_throw
# ---------------------------------------------------------------------------

class TestValidateThrow:
    # --- valid segments ---

    def test_segment_0_multiplier_1_is_valid(self):
        assert validate_throw(0, 1) is True

    def test_segment_1_multiplier_1_is_valid(self):
        assert validate_throw(1, 1) is True

    def test_segment_20_multiplier_1_is_valid(self):
        assert validate_throw(20, 1) is True

    def test_segment_20_multiplier_2_is_valid(self):
        assert validate_throw(20, 2) is True

    def test_segment_20_multiplier_3_is_valid(self):
        assert validate_throw(20, 3) is True

    def test_segment_10_multiplier_2_is_valid(self):
        assert validate_throw(10, 2) is True

    def test_bull_25_multiplier_1_is_valid(self):
        assert validate_throw(25, 1) is True

    def test_bullseye_50_multiplier_1_is_valid(self):
        assert validate_throw(50, 1) is True

    # --- invalid segments ---

    def test_segment_21_is_invalid(self):
        assert validate_throw(21, 1) is False

    def test_segment_negative_is_invalid(self):
        assert validate_throw(-1, 1) is False

    def test_segment_100_is_invalid(self):
        assert validate_throw(100, 1) is False

    def test_segment_30_is_invalid(self):
        # 30 is not a valid dartboard segment
        assert validate_throw(30, 1) is False

    # --- invalid multipliers ---

    def test_multiplier_0_is_invalid(self):
        assert validate_throw(10, 0) is False

    def test_multiplier_4_is_invalid(self):
        assert validate_throw(10, 4) is False

    def test_multiplier_negative_is_invalid(self):
        assert validate_throw(10, -1) is False

    # --- bull / bullseye / miss must be multiplier 1 ---

    def test_bull_25_multiplier_2_is_invalid(self):
        assert validate_throw(25, 2) is False

    def test_bull_25_multiplier_3_is_invalid(self):
        assert validate_throw(25, 3) is False

    def test_bullseye_50_multiplier_2_is_invalid(self):
        assert validate_throw(50, 2) is False

    def test_bullseye_50_multiplier_3_is_invalid(self):
        assert validate_throw(50, 3) is False

    def test_miss_0_multiplier_2_is_invalid(self):
        assert validate_throw(0, 2) is False

    def test_miss_0_multiplier_3_is_invalid(self):
        assert validate_throw(0, 3) is False


# ---------------------------------------------------------------------------
# is_bust
# ---------------------------------------------------------------------------

class TestIsBust:
    # --- negative score → bust ---

    def test_negative_score_is_bust(self):
        assert is_bust(-1, double_out=False, multiplier=1, segment=20) is True

    def test_large_negative_score_is_bust(self):
        assert is_bust(-60, double_out=False, multiplier=3, segment=20) is True

    # --- score == 1 → bust ---

    def test_score_one_is_bust(self):
        assert is_bust(1, double_out=False, multiplier=1, segment=1) is True

    # --- score == 0, no double-out → valid win, not bust ---

    def test_score_zero_no_double_out_is_not_bust(self):
        assert is_bust(0, double_out=False, multiplier=1, segment=20) is False

    def test_score_zero_no_double_out_with_single_is_not_bust(self):
        # Any finishing throw is fine when double_out=False
        assert is_bust(0, double_out=False, multiplier=3, segment=20) is False

    # --- score == 0, double-out enabled, finishing throw is NOT double → bust ---

    def test_score_zero_double_out_single_is_bust(self):
        assert is_bust(0, double_out=True, multiplier=1, segment=20) is True

    def test_score_zero_double_out_triple_is_bust(self):
        assert is_bust(0, double_out=True, multiplier=3, segment=20) is True

    # --- score == 0, double-out enabled, finishing throw IS double → not bust ---

    def test_score_zero_double_out_double_is_not_bust(self):
        assert is_bust(0, double_out=True, multiplier=2, segment=16) is False

    def test_score_zero_double_out_double_20_is_not_bust(self):
        assert is_bust(0, double_out=True, multiplier=2, segment=20) is False

    # --- score == 0, double-out enabled, finishing throw is bullseye (50) → not bust ---

    def test_score_zero_double_out_bullseye_is_not_bust(self):
        # Bullseye (segment=50) counts as a valid double-out finish
        assert is_bust(0, double_out=True, multiplier=1, segment=50) is False

    # --- positive score > 1 → never bust regardless of flags ---

    def test_positive_score_no_double_out_is_not_bust(self):
        assert is_bust(100, double_out=False, multiplier=1, segment=20) is False

    def test_positive_score_double_out_is_not_bust(self):
        assert is_bust(32, double_out=True, multiplier=1, segment=20) is False


# ---------------------------------------------------------------------------
# check_winner
# ---------------------------------------------------------------------------

class TestCheckWinner:
    def test_score_zero_is_winner(self):
        assert check_winner(0) is True

    def test_score_one_is_not_winner(self):
        assert check_winner(1) is False

    def test_score_positive_is_not_winner(self):
        assert check_winner(32) is False

    def test_score_negative_is_not_winner(self):
        # Negative scores should never reach check_winner in normal flow,
        # but the function must return False for any non-zero value.
        assert check_winner(-1) is False


# ---------------------------------------------------------------------------
# calculate_average_per_dart
# ---------------------------------------------------------------------------

class TestCalculateAveragePerDart:
    def test_normal_case(self):
        # 180 / 3 darts = 60.0
        result = calculate_average_per_dart(180, 3)
        assert result == 60.0

    def test_non_integer_average_rounds_to_two_places(self):
        # 100 / 3 ≈ 33.33
        result = calculate_average_per_dart(100, 3)
        assert result == round(100 / 3, 2)

    def test_zero_darts_returns_zero(self):
        assert calculate_average_per_dart(0, 0) == 0.0

    def test_zero_darts_with_nonzero_score_returns_zero(self):
        # Guard against division-by-zero; num_darts=0 always returns 0.0
        assert calculate_average_per_dart(500, 0) == 0.0

    def test_single_dart(self):
        assert calculate_average_per_dart(60, 1) == 60.0

    def test_zero_total_score_multiple_darts(self):
        # All misses
        assert calculate_average_per_dart(0, 6) == 0.0
