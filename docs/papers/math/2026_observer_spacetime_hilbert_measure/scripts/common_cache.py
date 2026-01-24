#!/usr/bin/env python3
"""Tiny cache helpers (paper-local).

We keep caches under .cache/ and use atomic writes to avoid partial files.
"""

from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path
from typing import Any

from common_paths import cache_dir


def cache_path(name: str) -> Path:
    p = cache_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_pickle(path: Path) -> Any:
    return pickle.loads(path.read_bytes())


def save_pickle_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

