from solvers.casinokeypad import calculate_key_sequence


def test_repeated_digit_only_presses_enter():
    moves = calculate_key_sequence([1, 1, 1, 1, 1, 1])
    assert moves == ["1", "return"] * 6


def test_max_swing_between_lowest_and_highest_digit():
    moves = calculate_key_sequence([5, 1, 5, 1, 5, 1])
    assert moves == [
        "s", "s", "s", "s", "return",
        "w", "w", "w", "w", "return",
        "s", "s", "s", "s", "return",
        "w", "w", "w", "w", "return",
        "s", "s", "s", "s", "return",
        "w", "w", "w", "w", "return",
    ]


def test_mixed_up_down_and_repeat_moves():
    moves = calculate_key_sequence([3, 2, 4, 4, 1, 5])
    assert moves == [
        "s", "s", "return",
        "w", "return",
        "s", "s", "return",
        "1", "return",
        "w", "w", "w", "return",
        "s", "s", "s", "s", "return",
    ]
