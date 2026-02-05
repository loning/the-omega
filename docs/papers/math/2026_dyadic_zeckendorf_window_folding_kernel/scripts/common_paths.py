#!/usr/bin/env python3
"""Common path utilities (paper-local, reproducible pipeline).

All generated LaTeX fragments live under sections/generated/,
and content-addressed experiment artifacts live under artifacts/.
"""

from __future__ import annotations

from pathlib import Path


def paper_root() -> Path:
    return Path(__file__).resolve().parents[1]


def scripts_dir() -> Path:
    return paper_root() / "scripts"


def generated_dir() -> Path:
    return paper_root() / "sections" / "generated"


def artifacts_dir() -> Path:
    return paper_root() / "artifacts"


def cache_dir() -> Path:
    return paper_root() / ".cache"

