# -*- coding: utf-8 -*-
"""
Deterministic on-disk caching helpers (pure stdlib).

Caching is enabled by default. To disable caching:
  export HPA_NO_CACHE=1
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Callable, TypeVar

from common_paths import scripts_dir

T = TypeVar("T")


def cache_disabled() -> bool:
    v = os.environ.get("HPA_NO_CACHE", "").strip().lower()
    return v in {"1", "true", "yes", "y"}


def cache_dir() -> Path:
    d = scripts_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_path(name: str) -> Path:
    return cache_dir() / name


def load_pickle(path: Path) -> T:
    with path.open("rb") as f:
        return pickle.load(f)


def save_pickle_atomic(path: Path, obj: T) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)


def load_or_compute(path: Path, compute: Callable[[], T]) -> T:
    if not cache_disabled() and path.is_file():
        try:
            return load_pickle(path)
        except Exception:
            pass
    obj = compute()
    if not cache_disabled():
        try:
            save_pickle_atomic(path, obj)
        except Exception:
            pass
    return obj

