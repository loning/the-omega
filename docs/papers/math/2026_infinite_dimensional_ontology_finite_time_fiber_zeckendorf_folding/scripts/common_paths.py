#!/usr/bin/env python3
"""
Paper-local path utilities for reproducible pipelines.
"""

from __future__ import annotations

from pathlib import Path


def paper_root() -> Path:
    return Path(__file__).resolve().parents[1]


def scripts_dir() -> Path:
    return paper_root() / "scripts"


def generated_dir() -> Path:
    return paper_root() / "sections" / "generated"

def generated_assets_dir() -> Path:
    return generated_dir() / "assets"


def artifacts_dir() -> Path:
    return paper_root() / "artifacts"


def cache_dir() -> Path:
    return paper_root() / ".cache"


def export_dir() -> Path:
    # All paper-referenced stable assets MUST live under sections/generated/.
    # This directory is intended for LaTeX \\includegraphics stable paths.
    return generated_assets_dir()

