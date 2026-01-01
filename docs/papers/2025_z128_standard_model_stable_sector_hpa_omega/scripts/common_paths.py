# -*- coding: utf-8 -*-
"""
Shared path helpers for reproducible scripts in this paper.

We keep all paths relative to the paper directory:
  docs/papers/2025_z128_standard_model_stable_sector_hpa_omega/

Only the Python standard library is used here.
"""

from __future__ import annotations

from pathlib import Path


def scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def paper_root() -> Path:
    # scripts/ -> paper root
    return scripts_dir().parent


def sections_dir() -> Path:
    return paper_root() / "sections"


def generated_dir() -> Path:
    return sections_dir() / "generated"


def figures_dir() -> Path:
    # Figures are optional; LaTeX can include them if present.
    return paper_root() / "figures"


