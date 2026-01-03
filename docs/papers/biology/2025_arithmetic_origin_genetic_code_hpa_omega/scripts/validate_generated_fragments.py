# -*- coding: utf-8 -*-
"""
Validate generated LaTeX fragments and their cache metadata.

Checks:
  - every sections/generated/*.tex is non-empty and contains at least one non-whitespace line
  - for every sections/generated/*.tex there is a *.tex.meta.json sidecar, and it contains a cache_digest
  - report (but do not fail) if there are meta files without a corresponding .tex (stale metas)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    return root_dir() / "sections" / "generated"


def _read_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read {label}: {path}") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"Malformed {label}: {path}")
    return obj


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate sections/generated/*.tex fragments and meta sidecars.")
    p.add_argument(
        "--dir",
        default=str(generated_dir()),
        help="Generated fragments directory (default: sections/generated).",
    )
    p.add_argument("--require-meta", action="store_true", help="Fail if a .tex fragment is missing .meta.json.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    d = Path(args.dir)
    if not d.exists():
        raise SystemExit(f"Missing generated dir: {d}")

    tex_files = sorted(d.glob("*.tex"))
    if not tex_files:
        raise SystemExit(f"No .tex fragments found under: {d}")

    missing_meta = 0
    empty_tex = 0
    bad_meta = 0

    for fp in tex_files:
        txt = fp.read_text(encoding="utf-8", errors="replace")
        if not any(line.strip() for line in txt.splitlines()):
            print(f"[bad] empty fragment: {fp.name}", flush=True)
            empty_tex += 1

        mp = fp.with_suffix(fp.suffix + ".meta.json")
        if not mp.exists():
            missing_meta += 1
            if args.require_meta:
                print(f"[bad] missing meta: {mp.name}", flush=True)
        else:
            meta = _read_json_dict(mp, label="fragment meta")
            if not isinstance(meta.get("cache_digest"), str) or len(str(meta.get("cache_digest"))) < 8:
                print(f"[bad] invalid cache_digest: {mp.name}", flush=True)
                bad_meta += 1

    stale_meta = 0
    for mp in sorted(d.glob("*.tex.meta.json")):
        fp = Path(str(mp)[: -len(".meta.json")])
        if not fp.exists():
            stale_meta += 1

    print("OK" if (empty_tex == 0 and bad_meta == 0 and (missing_meta == 0 or not args.require_meta)) else "WARN", flush=True)
    print(f"fragments={len(tex_files)} empty={empty_tex} missing_meta={missing_meta} bad_meta={bad_meta} stale_meta={stale_meta}", flush=True)

    if empty_tex > 0:
        raise SystemExit("Some generated fragments are empty.")
    if bad_meta > 0:
        raise SystemExit("Some fragment meta sidecars are malformed.")
    if args.require_meta and missing_meta > 0:
        raise SystemExit("Missing meta sidecars for some fragments.")


if __name__ == "__main__":
    main()


