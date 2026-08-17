"""Canonical maximum-subarray utilities."""
from __future__ import annotations

from collections.abc import Sequence


def _validate_input(arr: Sequence[int]) -> None:
    """Validate the public maximum-subarray input."""
    if not isinstance(arr, (list, tuple)):
        raise TypeError("arr must be a list or tuple of integers")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in arr):
        raise TypeError("arr must contain only integers")


def find_max_subarray(arr: Sequence[int]) -> tuple[int, list[int]]:
    """Return the largest contiguous-subarray sum and the subarray itself.

    Empty input returns ``(0, [])``. For non-empty input, the selected
    subarray contains at least one element, so an all-negative input returns
    its largest element and the corresponding one-element subarray.
    """
    _validate_input(arr)
    if not arr:
        return 0, []

    current_sum = best_sum = arr[0]
    current_start = best_start = 0
    best_end = 0

    for index, value in enumerate(arr[1:], start=1):
        if value > current_sum + value:
            current_sum = value
            current_start = index
        else:
            current_sum += value

        if current_sum > best_sum:
            best_sum = current_sum
            best_start = current_start
            best_end = index

    return best_sum, list(arr[best_start : best_end + 1])


def find_max_subarray_sum(arr: Sequence[int]) -> int:
    """Return only the largest contiguous-subarray sum."""
    return find_max_subarray(arr)[0]
