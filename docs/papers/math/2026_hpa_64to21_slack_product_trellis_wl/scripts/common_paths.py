# -*- coding: utf-8 -*-
"""
Shared path helpers for reproducible scripts in this paper.

All paths are relative to:
  docs/papers/math/2026_hpa_64to21_slack_product_trellis_wl/

Standard-library only.
"""

from __future__ import annotations

from pathlib import Path


def scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def paper_root() -> Path:
    return scripts_dir().parent


def sections_dir() -> Path:
    return paper_root() / "sections"


def generated_dir() -> Path:
    return sections_dir() / "generated"

