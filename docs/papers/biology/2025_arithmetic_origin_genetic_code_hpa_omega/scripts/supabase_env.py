# -*- coding: utf-8 -*-
"""
Minimal .env-style loader (standard library only).

We intentionally do not use dotenv dependencies in this repo.
"""

from __future__ import annotations

from pathlib import Path


def load_env_file(path: Path) -> dict[str, str]:
    """
    Parse KEY=VALUE lines. Supports:
      - Blank lines
      - Comment lines starting with '#'
      - Values optionally quoted with single/double quotes
    """
    out: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        out[k] = v
    return out


