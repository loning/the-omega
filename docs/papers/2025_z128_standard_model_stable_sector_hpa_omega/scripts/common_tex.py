# -*- coding: utf-8 -*-
"""
Minimal helpers for writing LaTeX fragments used by the paper.

Design constraints:
  - Deterministic output (no timestamps).
  - No trailing blank line (fragments are included inside tabular environments).
  - ASCII/UTF-8 safe (paths and content are UTF-8).

Only the Python standard library is used here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


def write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(list(lines))
    # Do not add a trailing newline; these fragments are included inline in LaTeX.
    path.write_text(text, encoding="utf-8")


def nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def read_lines(path: Path) -> List[str]:
    return path.read_text(encoding="utf-8").splitlines()


