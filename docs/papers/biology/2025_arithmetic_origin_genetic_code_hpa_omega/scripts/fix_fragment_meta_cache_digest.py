# -*- coding: utf-8 -*-
"""
Repair/normalize cache metadata sidecars for generated LaTeX fragments.

Some historical fragments shipped with *.tex.meta.json files that omit the
required `cache_digest` field. This script adds a deterministic digest so that
`validate_generated_fragments.py` passes.

By default:
  - if `cache_key` exists and is a dict, digest = cache_key_digest(cache_key)
  - else digest = cache_key_digest(meta_without_cache_digest)
  - we do NOT add/overwrite `cache_key` (optional via --write-cache-key)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cache_manager import cache_key_digest, write_json_atomic


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fix missing/invalid cache_digest in *.tex.meta.json files.")
    p.add_argument(
        "--dir",
        default=str(root_dir() / "sections" / "generated"),
        help="Generated fragments directory (default: sections/generated).",
    )
    p.add_argument("--write-cache-key", action="store_true", help="Also write cache_key when absent (off by default).")
    return p.parse_args()


def _read_json_dict(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"Failed to read JSON: {path}") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"Malformed JSON (expected dict): {path}")
    return obj


def main() -> None:
    args = parse_args()
    d = Path(str(args.dir))
    if not d.exists():
        raise SystemExit(f"Missing dir: {d}")

    changed = 0
    total = 0

    for mp in sorted(d.glob("*.tex.meta.json")):
        total += 1
        meta = _read_json_dict(mp)
        cd = meta.get("cache_digest")
        if isinstance(cd, str) and len(cd) >= 8:
            continue

        ck = meta.get("cache_key")
        if isinstance(ck, dict):
            cache_key = ck
        else:
            cache_key = {k: v for k, v in meta.items() if k != "cache_digest"}

        meta["cache_digest"] = cache_key_digest(cache_key)
        if args.write_cache_key and not isinstance(meta.get("cache_key"), dict):
            meta["cache_key"] = cache_key

        write_json_atomic(mp, meta)
        changed += 1

    print(f"Scanned {total} meta files; updated {changed}.", flush=True)


if __name__ == "__main__":
    main()

