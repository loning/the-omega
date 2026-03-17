#!/usr/bin/env python3
"""Emit anchor tasks for labels referenced in merged TeX but missing in DAG atoms."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from _kg_common import (
    default_kg_root,
    extract_tex_crossrefs,
    slugify,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit tex_knowledge_unit anchor tasks for unresolved reference labels."
    )
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--merged-tex", type=Path, required=True, help="Merged TeX path")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Task output dir (default: <kg-root>/.kgcache/llm_queue)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        help="Max emitted anchors (0 means all)",
    )
    return parser.parse_args()


def read_json(path: Path) -> Dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def existing_source_tex_labels(kg_root: Path) -> Set[str]:
    atoms_dir = kg_root / "atoms"
    out: Set[str] = set()
    if not atoms_dir.exists():
        return out
    for meta_path in atoms_dir.glob("*.meta.json"):
        rec = read_json(meta_path)
        label = str(rec.get("source_tex_label") or "").strip()
        if label:
            out.add(label)
    return out


def parse_reference_targets(merged_tex: Path) -> Set[str]:
    text = merged_tex.read_text(encoding="utf-8", errors="replace")
    _, refs, _ = extract_tex_crossrefs(text)
    out = {x.strip() for x in refs if x and x.strip()}
    # Never generate anchors for internal synthetic labels.
    out = {x for x in out if not x.startswith("kgid:")}
    return out


def canonical_from_ref(ref_label: str) -> str:
    return f"anchor-{slugify(ref_label)}"


def unit_tex_for_label(label: str) -> str:
    return (
        "\\phantomsection\n"
        f"\\label{{{label}}}\n"
    )


def task_filename(label: str) -> str:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:16]
    return f"task_anchor_{digest}.json"


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    merged_tex = args.merged_tex.resolve()
    out_dir = args.out_dir.resolve() if args.out_dir else (kg_root / ".kgcache" / "llm_queue")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not merged_tex.exists():
        raise SystemExit(f"merged TeX does not exist: {merged_tex}")

    existing = existing_source_tex_labels(kg_root)
    refs = parse_reference_targets(merged_tex)
    missing = sorted(refs - existing)
    if args.max > 0:
        missing = missing[: args.max]

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    created = 0
    skipped_existing_task = 0
    for idx, ref_label in enumerate(missing, start=1):
        filename = task_filename(ref_label)
        path = out_dir / filename
        if path.exists():
            skipped_existing_task += 1
            continue
        task = {
            "task_id": f"TASK-ANCHOR-{ts}-{idx:06d}",
            "created_at": ts,
            "source_name": "merged_anchor_backfill",
            "change_type": "backfill",
            "source_path": str(merged_tex),
            "old_hash": "",
            "new_hash": "",
            "suggested_node_type": "tp-note",
            "task_kind": "tex_knowledge_unit",
            "canonical_label": canonical_from_ref(ref_label),
            "source_tex_label": ref_label,
            "source_refs": [],
            "unit_tex": unit_tex_for_label(ref_label),
            "unit_env": "label_anchor",
            "status": "pending",
        }
        path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        created += 1

    print(f"merged_ref_targets={len(refs)}")
    print(f"existing_source_tex_labels={len(existing)}")
    print(f"missing_ref_targets={len(refs - existing)}")
    print(f"emitted_anchor_tasks={created}")
    print(f"skipped_existing_task_files={skipped_existing_task}")
    print(f"out_dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
