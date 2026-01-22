# -*- coding: utf-8 -*-
"""
Minimal helpers for writing generated LaTeX fragments.

Design constraints:
  - Deterministic output (no timestamps).
  - No trailing blank line (fragments are included by \\input).
"""

from __future__ import annotations

from pathlib import Path


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text), encoding="utf-8")


def nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False

