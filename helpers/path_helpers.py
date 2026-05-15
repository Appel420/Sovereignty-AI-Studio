"""
Path and file system utility functions.
"""

import pathlib
from typing import Union

from errors.exceptions import ValidationError

PathLike = Union[str, pathlib.Path]


def ensure_dir(path: PathLike) -> pathlib.Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Path object for the directory

    Raises:
        ValidationError: If path exists but is not a directory
    """
    p = pathlib.Path(path)

    if p.exists() and not p.is_dir():
        raise ValidationError(f"Path exists but is not a directory: {p}")

    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_path_join(base: PathLike, *parts: str) -> pathlib.Path:
    """
    Safely join path components, preventing directory traversal.

    Args:
        base: Base directory path
        *parts: Path components to join

    Returns:
        Resolved path within base directory

    Raises:
        ValidationError: If resolved path is outside base directory
    """
    base_path = pathlib.Path(base).resolve()
    joined = base_path.joinpath(*parts).resolve()

    # Ensure joined path is within base directory
    try:
        joined.relative_to(base_path)
    except ValueError as e:
        raise ValidationError(
            f"Path traversal detected: {parts}",
            details={"base": str(base_path), "attempted": str(joined)},
        ) from e

    return joined


def get_data_dir() -> pathlib.Path:
    """
    Get the data directory path, creating it if necessary.

    Returns:
        Path to data directory
    """
    # Assumes this helper module is at <root>/helpers/
    root = pathlib.Path(__file__).parent.parent
    data_dir = root / "data"
    return ensure_dir(data_dir)


def get_logs_dir() -> pathlib.Path:
    """
    Get the logs directory path, creating it if necessary.

    Returns:
        Path to logs directory
    """
    # Assumes this helper module is at <root>/helpers/
    root = pathlib.Path(__file__).parent.parent
    logs_dir = root / "logs"
    return ensure_dir(logs_dir)
