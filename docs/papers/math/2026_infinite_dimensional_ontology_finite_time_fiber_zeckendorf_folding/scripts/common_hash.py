#!/usr/bin/env python3
"""
Hashing helpers for reproducible, content-addressed artifacts.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def sha256_json(obj: Dict[str, Any]) -> str:
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(s.encode("utf-8"))


def git_head_sha(p: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(p.resolve()), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode("utf-8").strip()
    except Exception:
        return ""


def python_runtime() -> str:
    return sys.version.replace("\n", " ").strip()

