#!/usr/bin/env python3
"""Upgrade atom sidecars to typed edge schema (parent_edges)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from _kg_common import (
    atom_sidecar_path,
    default_kg_root,
    now_utc_compact,
    parse_parent_edges,
    parse_parent_labels_from_meta,
    scan_atoms,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upgrade sidecar to edge schema v2.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--apply", action="store_true", help="Write upgraded sidecars")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Output report path (default: <kg-root>/.kgcache/visuals/dag_edge_schema_upgrade_report.json)",
    )
    return parser.parse_args()


def infer_edge_fields(meta: Dict[str, object], parent: str) -> Dict[str, object]:
    task_kind = str(meta.get("task_kind") or "")
    relink_version = str(meta.get("relink_version") or "")
    relink_reasons = meta.get("relink_reasons")

    if task_kind == "synthetic_component_bridge":
        return {
            "parent": parent,
            "edge_type": "bridge_component",
            "edge_source": "kg_bridge_components",
            "edge_reason": "component_merge_tree",
        }
    if relink_version:
        reason = "relinked"
        if isinstance(relink_reasons, list) and relink_reasons:
            reason = str(relink_reasons[0] or "relinked")
        return {
            "parent": parent,
            "edge_type": "relink",
            "edge_source": "kg_relink_islands",
            "edge_reason": reason,
        }
    if task_kind == "tex_knowledge_unit":
        return {
            "parent": parent,
            "edge_type": "inference_ref",
            "edge_source": "kg_ingest_atoms",
            "edge_reason": "source_refs",
        }
    return {
        "parent": parent,
        "edge_type": "inference_candidate",
        "edge_source": "kg_ingest_atoms",
        "edge_reason": "legacy_parent_projection",
    }


def edge_signature(edge: Dict[str, object]) -> str:
    return json.dumps(edge, ensure_ascii=False, sort_keys=True)


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    report_path = (
        args.report.resolve()
        if args.report
        else (kg_root / ".kgcache" / "visuals" / "dag_edge_schema_upgrade_report.json")
    )

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        print("scan errors:")
        for err in scan_errors[:50]:
            print(f"- {err}")
        return 2

    updated = 0
    unchanged = 0
    missing_sidecar = 0
    edge_type_counts = Counter()
    upgraded_at = now_utc_compact()
    sample_updates: List[Dict[str, object]] = []

    for atom in atoms:
        sidecar = atom_sidecar_path(atom.path)
        if not sidecar.exists():
            missing_sidecar += 1
            continue
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(meta, dict):
            continue

        parent_labels = parse_parent_labels_from_meta(meta)
        existing_edge_map = {str(e.get("parent")): dict(e) for e in parse_parent_edges(meta)}

        new_edges: List[Dict[str, object]] = []
        for parent in parent_labels:
            existing = existing_edge_map.get(parent)
            if existing:
                row = dict(existing)
                row["parent"] = parent
            else:
                row = infer_edge_fields(meta, parent)
            new_edges.append(row)
            edge_type_counts[str(row.get("edge_type") or "unknown")] += 1

        new_meta = dict(meta)
        new_meta["parents"] = parent_labels
        new_meta["parent_edges"] = new_edges
        new_meta["edge_schema_version"] = "v2"
        new_meta["edge_schema_upgraded_at"] = upgraded_at

        old_sig = edge_signature(
            {
                "parents": parse_parent_labels_from_meta(meta),
                "parent_edges": parse_parent_edges(meta),
                "edge_schema_version": str(meta.get("edge_schema_version") or ""),
            }
        )
        new_sig = edge_signature(
            {
                "parents": parent_labels,
                "parent_edges": new_edges,
                "edge_schema_version": "v2",
            }
        )
        changed = old_sig != new_sig
        if changed:
            updated += 1
            if len(sample_updates) < 80:
                sample_updates.append(
                    {
                        "label": atom.label,
                        "kg_id": atom.kg_id,
                        "edge_count": len(new_edges),
                        "task_kind": str(new_meta.get("task_kind") or ""),
                    }
                )
            if args.apply:
                write_json(sidecar, new_meta)
        else:
            unchanged += 1
            if args.apply and str(meta.get("edge_schema_version") or "") != "v2":
                write_json(sidecar, new_meta)

    report = {
        "kg_root": str(kg_root),
        "apply": bool(args.apply),
        "atoms_total": len(atoms),
        "updated_count": updated,
        "unchanged_count": unchanged,
        "missing_sidecar_count": missing_sidecar,
        "edge_type_counts": dict(edge_type_counts.most_common()),
        "sample_updates": sample_updates,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"report: {report_path}")
    print(
        f"apply={args.apply} atoms={len(atoms)} updated={updated} "
        f"unchanged={unchanged} missing_sidecar={missing_sidecar}"
    )
    if edge_type_counts:
        print("edge_type_counts:")
        for key, value in edge_type_counts.most_common(12):
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
