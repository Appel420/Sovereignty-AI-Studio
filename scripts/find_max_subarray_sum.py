#!/usr/bin/env python3
"""Compatibility entry point for the canonical maximum-subarray utility."""
from __future__ import annotations

from src.utils.max_subarray import find_max_subarray, find_max_subarray_sum

__all__ = ["find_max_subarray", "find_max_subarray_sum"]


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
