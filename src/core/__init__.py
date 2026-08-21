"""Core runtime package with compatibility access to root security modules.

The repository contains historical ``core`` modules in both ``src/core`` and
``core``. Test and runtime import order can make either package load first, so
this package explicitly extends its module search path to the root-level
``core`` directory. That keeps ``core.security`` available without depending on
ambient ``PYTHONPATH`` ordering.
"""
from __future__ import annotations

from pathlib import Path

_ROOT_CORE = Path(__file__).resolve().parents[2] / "core"
if _ROOT_CORE.is_dir():
    _root_core_path = str(_ROOT_CORE)
    if _root_core_path not in __path__:
        __path__.append(_root_core_path)
