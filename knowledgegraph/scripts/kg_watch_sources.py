#!/usr/bin/env python3
"""Watch configured source directories and emit hash deltas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Tuple

from _kg_common import (
    compute_sha256,
    default_kg_root,
    ensure_dir,
    load_source_spec,
    now_utc_compact,
)


def expand_spec_paths(kg_root: Path, specs: Iterable[str]) -> List[Path]:
    if specs:
        out: List[Path] = []
        for spec in specs:
            path = Path(spec)
            if path.is_absolute() and path.exists():
                out.append(path)
                continue

            matched = list((kg_root).glob(spec))
            if matched:
                out.extend(matched)
                continue

            candidate = kg_root / spec
            if candidate.exists():
                out.append(candidate)
        return sorted(set(p.resolve() for p in out))

    default_dir = kg_root / "source_specs"
    if not default_dir.exists():
        return []
    return sorted(p.resolve() for p in default_dir.glob("*.src"))


def matches(rel_posix: str, patterns: Tuple[str, ...]) -> bool:
    if not patterns:
        return True
    p = PurePosixPath(rel_posix)
    return any(p.match(pat) for pat in patterns)


def build_snapshot(root: Path, include: Tuple[str, ...], exclude: Tuple[str, ...]) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if not matches(rel, include):
            continue
        if exclude and matches(rel, exclude):
            continue
        snapshot[rel] = compute_sha256(path)
    return snapshot


def detect_renames(added: Dict[str, str], deleted: Dict[str, str]) -> List[Tuple[str, str, str]]:
    hash_to_added: Dict[str, List[str]] = {}
    for path, h in added.items():
        hash_to_added.setdefault(h, []).append(path)

    renames: List[Tuple[str, str, str]] = []
    used_new: set[str] = set()
    for old_path, old_hash in sorted(deleted.items()):
        candidates = hash_to_added.get(old_hash, [])
        target = None
        for c in sorted(candidates):
            if c not in used_new:
                target = c
                break
        if target is not None:
            used_new.add(target)
            renames.append((old_path, target, old_hash))

    return renames


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect source hash changes and emit deltas.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help="Spec path or glob (repeatable). If omitted, source_specs/*.src is used.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

    spec_paths = expand_spec_paths(kg_root, args.spec)
    if not spec_paths:
        print("No source spec files found.")
        return 1

    ts = now_utc_compact()
    total_changes = 0

    for spec_path in spec_paths:
        spec = load_source_spec(spec_path, kg_root)
        if not spec.root.exists():
            print(f"WARN: source root does not exist, skip: {spec.root}")
            continue

        source_cache = kg_root / ".kgcache" / "source" / spec.name
        ensure_dir(source_cache)

        snapshot_latest_path = source_cache / "snapshot_latest.json"
        prev_snapshot: Dict[str, str] = {}
        if snapshot_latest_path.exists():
            prev_snapshot = json.loads(snapshot_latest_path.read_text(encoding="utf-8"))

        cur_snapshot = build_snapshot(spec.root, spec.include, spec.exclude)

        added = {p: h for p, h in cur_snapshot.items() if p not in prev_snapshot}
        deleted = {p: h for p, h in prev_snapshot.items() if p not in cur_snapshot}
        modified = {
            p: (prev_snapshot[p], cur_snapshot[p])
            for p in cur_snapshot.keys() & prev_snapshot.keys()
            if cur_snapshot[p] != prev_snapshot[p]
        }

        renames = detect_renames(added, deleted)
        for old_rel, new_rel, h in renames:
            added.pop(new_rel, None)
            deleted.pop(old_rel, None)

        delta_path = source_cache / f"delta_{ts}.jsonl"
        records = []

        for rel, h in sorted(added.items()):
            records.append(
                {
                    "timestamp": ts,
                    "source_name": spec.name,
                    "source_root": str(spec.root),
                    "change_type": "added",
                    "rel_path": rel,
                    "path": str(spec.root / rel),
                    "old_hash": None,
                    "new_hash": h,
                }
            )

        for rel, (old_h, new_h) in sorted(modified.items()):
            records.append(
                {
                    "timestamp": ts,
                    "source_name": spec.name,
                    "source_root": str(spec.root),
                    "change_type": "modified",
                    "rel_path": rel,
                    "path": str(spec.root / rel),
                    "old_hash": old_h,
                    "new_hash": new_h,
                }
            )

        for rel, h in sorted(deleted.items()):
            records.append(
                {
                    "timestamp": ts,
                    "source_name": spec.name,
                    "source_root": str(spec.root),
                    "change_type": "deleted",
                    "rel_path": rel,
                    "path": str(spec.root / rel),
                    "old_hash": h,
                    "new_hash": None,
                }
            )

        for old_rel, new_rel, h in sorted(renames):
            records.append(
                {
                    "timestamp": ts,
                    "source_name": spec.name,
                    "source_root": str(spec.root),
                    "change_type": "renamed",
                    "old_rel_path": old_rel,
                    "new_rel_path": new_rel,
                    "old_path": str(spec.root / old_rel),
                    "new_path": str(spec.root / new_rel),
                    "old_hash": h,
                    "new_hash": h,
                }
            )

        delta_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + ("\n" if records else ""),
            encoding="utf-8",
        )

        (source_cache / f"snapshot_{ts}.json").write_text(
            json.dumps(cur_snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        snapshot_latest_path.write_text(
            json.dumps(cur_snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        total_changes += len(records)
        print(
            f"[{spec.name}] added={len(added)} modified={len(modified)} "
            f"deleted={len(deleted)} renamed={len(renames)} delta={delta_path}"
        )

    print(f"Total change records: {total_changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
