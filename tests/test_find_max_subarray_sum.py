from __future__ import annotations

import pytest

from scripts.find_max_subarray_sum import find_max_subarray, find_max_subarray_sum
from src.utils import find_max_subarray as public_find_max_subarray
from src.utils import find_max_subarray_sum as public_find_max_subarray_sum


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


def test_returns_sum_and_subarray() -> None:
    assert find_max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == (
        6,
        [4, -1, 2, 1],
    )


def test_all_negative_returns_best_element_and_subarray() -> None:
    assert find_max_subarray([-5, -2, -9]) == (-2, [-2])


def test_empty_returns_zero_and_empty_subarray() -> None:
    assert find_max_subarray([]) == (0, [])


@pytest.mark.parametrize("value", [None, "1", 1.5, {1}, (1, "2")])
def test_rejects_invalid_input(value: object) -> None:
    with pytest.raises(TypeError):
        find_max_subarray_sum(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [[1, "2"], [True, 1], [1, False], [1.0]])
def test_rejects_non_integer_elements(value: object) -> None:
    with pytest.raises(TypeError):
        find_max_subarray(value)  # type: ignore[arg-type]


def test_public_import_path() -> None:
    values = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
    assert public_find_max_subarray_sum(values) == 6
    assert public_find_max_subarray(values) == (6, [4, -1, 2, 1])
