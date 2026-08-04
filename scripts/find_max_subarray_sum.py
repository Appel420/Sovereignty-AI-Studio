#!/usr/bin/env python3
"""Maximum contiguous subarray sum using Kadane's algorithm."""
from __future__ import annotations


def find_max_subarray_sum(arr: list[int]) -> int:
    """Return the largest sum of any contiguous subarray.

    Empty input returns 0. For non-empty input, a subarray must contain at
    least one element, so an all-negative array returns its largest element.
    """
    if not arr:
        return 0

    current_max = max_so_far = arr[0]
    for value in arr[1:]:
        current_max = max(value, current_max + value)
        max_so_far = max(max_so_far, current_max)

    return max_so_far


if __name__ == "__main__":
    examples = (
        [-2, 1, -3, 4, -1, 2, 1, -5, 4],
        [1],
        [5, 4, -1, 7, 8],
        [-1, -2, -3, -4],
        [],
    )
    for example in examples:
        print(f"{example}: {find_max_subarray_sum(example)}")
