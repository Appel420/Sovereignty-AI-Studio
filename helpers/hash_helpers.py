"""
Hash and checksum utility functions.
"""

import hashlib
from typing import Literal

HashAlgorithm = Literal["sha256", "sha3-512", "md5"]


def sha256(data: str | bytes) -> str:
    """
    Calculate SHA-256 hash of data.

    Args:
        data: Data to hash (string or bytes)

    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha3_512(data: str | bytes) -> str:
    """
    Calculate SHA3-512 hash of data.

    Args:
        data: Data to hash (string or bytes)

    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha3_512(data).hexdigest()


def calculate_checksum(data: str | bytes, algorithm: HashAlgorithm = "sha256") -> str:
    """
    Calculate checksum using specified algorithm.

    Args:
        data: Data to checksum
        algorithm: Hash algorithm to use (sha256, sha3-512, md5)

    Returns:
        Hexadecimal checksum string
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    elif algorithm == "sha3-512":
        return hashlib.sha3_512(data).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def verify_checksum(
    data: str | bytes,
    expected_checksum: str,
    algorithm: HashAlgorithm = "sha256",
) -> bool:
    """
    Verify data matches expected checksum.

    Args:
        data: Data to verify
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm used for checksum

    Returns:
        True if checksum matches, False otherwise
    """
    actual_checksum = calculate_checksum(data, algorithm)
    return actual_checksum.lower() == expected_checksum.lower()
