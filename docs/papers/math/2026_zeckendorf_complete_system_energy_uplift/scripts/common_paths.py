#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common path utilities (paper-local, reproducible pipeline)."""

from __future__ import annotations

from pathlib import Path


def paper_root() -> Path:
    return Path(__file__).resolve().parents[1]


def scripts_dir() -> Path:
    return paper_root() / "scripts"


def artifacts_dir() -> Path:
    return paper_root() / "artifacts"


def cache_dir() -> Path:
    return paper_root() / ".cache"


def generated_dir() -> Path:
    return paper_root() / "sections" / "generated"


def export_dir() -> Path:
    """Fixed, human-facing exports for the paper."""
    return artifacts_dir() / "export"

