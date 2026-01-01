# -*- coding: utf-8 -*-
"""
Small caching helpers (standard library only).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def stable_json_dumps(obj: Any) -> str:
    """
    Deterministic JSON string used for cache-key hashing.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def cache_key_digest(obj: Any, *, n_hex: int = 16) -> str:
    """
    Return a short hex digest of the cache key.
    """
    h = hashlib.sha256(stable_json_dumps(obj).encode("utf-8"))
    return h.hexdigest()[: int(n_hex)]


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_json_atomic(path: Path, obj: Any) -> None:
    write_text_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def cache_meta_path(output_path: Path) -> Path:
    return output_path.with_suffix(output_path.suffix + ".meta.json")


def cache_hit(output_path: Path, *, expected_meta: dict[str, Any], require_meta: bool = False) -> bool:
    """
    Cache hit if output exists and meta exists and matches the expected meta.
    If output exists but meta is missing:
      - require_meta=False: treat as hit (back-compat) and allow caller to write meta.
      - require_meta=True: treat as miss.
    """
    if not output_path.exists():
        return False
    mp = cache_meta_path(output_path)
    if not mp.exists():
        return not require_meta
    try:
        meta = read_json(mp)
    except Exception:
        return False
    return meta == expected_meta


