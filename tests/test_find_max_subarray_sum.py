from __future__ import annotations

from scripts.find_max_subarray_sum import find_max_subarray_sum


def test_mixed_values() -> None:
    assert find_max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6


def test_all_positive_values() -> None:
    assert find_max_subarray_sum([5, 4, -1, 7, 8]) == 23


def test_all_negative_values() -> None:
    assert find_max_subarray_sum([-1, -2, -3, -4]) == -1


def test_single_value() -> None:
    assert find_max_subarray_sum([1]) == 1


def test_empty_input() -> None:
    assert find_max_subarray_sum([]) == 0
