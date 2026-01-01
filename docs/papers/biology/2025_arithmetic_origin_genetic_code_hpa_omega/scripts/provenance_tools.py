# -*- coding: utf-8 -*-
"""
Small helpers for provenance / version inference (standard library only).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cache_manager import cache_meta_path, read_json


def _as_pos_int(x: object) -> int | None:
    try:
        v = int(x)  # type: ignore[arg-type]
    except Exception:
        return None
    return v if v > 0 else None


def infer_analysis_version(summary_path: Path, *, summary_obj: dict[str, Any] | None = None) -> int | None:
    """
    Infer analysis_version with the following priority:
      1) summary JSON field: analysis_version
      2) summary sidecar meta JSON: cache_key.analysis_version
      3) summary JSON field: schema_version (back-compat)

    Returns None if nothing usable is found.
    """
    obj: Any
    if summary_obj is None:
        try:
            obj = read_json(summary_path)
        except Exception:
            return None
    else:
        obj = summary_obj

    if isinstance(obj, dict):
        av = _as_pos_int(obj.get("analysis_version"))
        if av is not None:
            return av

        mp = cache_meta_path(summary_path)
        if mp.exists():
            try:
                meta = read_json(mp)
            except Exception:
                meta = None
            if isinstance(meta, dict):
                ck = meta.get("cache_key")
                if isinstance(ck, dict):
                    av2 = _as_pos_int(ck.get("analysis_version"))
                    if av2 is not None:
                        return av2

        # Last-resort back-compat.
        sv = _as_pos_int(obj.get("schema_version"))
        if sv is not None:
            return sv

    return None


