# -*- coding: utf-8 -*-
"""
Validate that datasets referenced by data/manifest.json are available locally.

This is intended for offline reproducibility runs (e.g. run_all.py --no-download).

Checks (best-effort, schema-tolerant):
  - manifest.json is parseable
  - every dataset entry has a local_dir that exists
  - for ncbi_refseq_dir datasets:
      * if "files" is present and non-empty: each listed file exists under local_dir
      * otherwise: at least one *.gz exists under local_dir
  - every panel item references an existing dataset key

Standard library only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def read_manifest() -> dict[str, Any]:
    mp = root_dir() / "data" / "manifest.json"
    return json.loads(mp.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate local dataset availability for manifest.json.")
    p.add_argument("--warn-only", action="store_true", help="Do not fail on missing files/dirs; print warnings.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    m = read_manifest()
    datasets = m.get("datasets") or {}
    panels = m.get("panels") or {}

    if not isinstance(datasets, dict):
        raise SystemExit("manifest.json: 'datasets' must be an object")
    if not isinstance(panels, dict):
        raise SystemExit("manifest.json: 'panels' must be an object")

    missing: list[str] = []
    warnings: list[str] = []

    for key, ds in datasets.items():
        if not isinstance(ds, dict):
            warnings.append(f"[warn] dataset '{key}' is not an object; skipping")
            continue
        ds_type = str(ds.get("type") or "")
        local_dir = ds.get("local_dir")
        local_path = ds.get("local_path")

        if isinstance(local_dir, str) and local_dir.strip():
            ld = root_dir() / local_dir
            if not ld.exists():
                missing.append(f"[missing] dataset '{key}' local_dir not found: {ld}")
                continue
            if ds_type == "ncbi_refseq_dir":
                files = ds.get("files") or []
                if isinstance(files, list) and any(isinstance(x, dict) for x in files):
                    expected = []
                    for e in files:
                        if not isinstance(e, dict):
                            continue
                        name = e.get("name")
                        if isinstance(name, str) and name:
                            expected.append(ld / name)
                    if expected:
                        for fp in expected:
                            if not fp.exists():
                                missing.append(f"[missing] dataset '{key}' file not found: {fp}")
                    else:
                        # Fallback: require at least one .gz
                        if not any(ld.glob("*.gz")):
                            missing.append(f"[missing] dataset '{key}' has no listed files and no *.gz under: {ld}")
                else:
                    if not any(ld.glob("*.gz")):
                        missing.append(f"[missing] dataset '{key}' has no *.gz under: {ld}")
            continue

        if isinstance(local_path, str) and local_path.strip():
            fp = root_dir() / local_path
            if not fp.exists():
                missing.append(f"[missing] dataset '{key}' local_path not found: {fp}")
            continue

        # Some composite entries record multiple paths (e.g. recoding GenBank bundles); skip quietly.
        if ds_type in {"composite", "bundle"}:
            continue

        if ds_type == "file":
            missing.append(f"[missing] dataset '{key}' has type=file but no local_path")
        else:
            warnings.append(f"[warn] dataset '{key}' has no local_dir/local_path (type={ds_type}); skipping")

    # Panels: ensure dataset keys exist.
    for panel_key, panel in panels.items():
        if not isinstance(panel, dict):
            continue
        items = panel.get("items") or []
        if not isinstance(items, list):
            continue
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                continue
            ds_key = it.get("dataset")
            if isinstance(ds_key, str) and ds_key:
                if ds_key not in datasets:
                    missing.append(f"[missing] panel '{panel_key}' item[{i}] references unknown dataset: {ds_key}")

    for w in warnings:
        print(w)
    for x in missing:
        print(x)

    if missing and not args.warn_only:
        raise SystemExit(f"Missing local resources: {len(missing)}")
    print("OK" if not missing else "WARN")


if __name__ == "__main__":
    main()


