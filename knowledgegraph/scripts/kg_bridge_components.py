#!/usr/bin/env python3
"""Connect weakly disconnected DAG components by adding synthetic bridge atoms."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

from _kg_common import (
    Atom,
    atom_sidecar_path,
    default_kg_root,
    hash12_for_bytes,
    parallel_kg_id_factory,
    scan_atoms,
    write_json,
)

STATEMENT_TYPES: Set[str] = {
    "tp-def",
    "tp-axiom",
    "tp-lemma",
    "tp-thm",
    "tp-cor",
    "tp-prop",
    "tp-claim",
    "tp-conj",
}
KG_ID_RE = re.compile(r"^KG-(?P<date>\d{8})-(?P<seq>\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge weak components into one connected DAG.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--apply", action="store_true", help="Persist synthetic bridge atoms")
    parser.add_argument(
        "--max-parents",
        type=int,
        default=6,
        help="Max parents per bridge atom (tree fan-in)",
    )
    parser.add_argument(
        "--prefix",
        default="bridge-cc",
        help="Bridge label prefix",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Output report path (default: <kg-root>/.kgcache/visuals/dag_bridge_components_report.json)",
    )
    return parser.parse_args()


def kg_id_sort_key(kg_id: str) -> Tuple[str, int]:
    m = KG_ID_RE.match(kg_id)
    if not m:
        return "", -1
    return m.group("date"), int(m.group("seq"))


def next_kg_id_factory(kg_root: Path, now: datetime):
    _ = kg_root  # Kept for backward-compatible signature.
    return parallel_kg_id_factory(now)


def build_components(atoms: Sequence[Atom]) -> Tuple[Dict[str, int], Dict[str, int], List[List[str]]]:
    by_label = {a.label: a for a in atoms}
    labels = set(by_label.keys())
    in_deg = {lb: 0 for lb in labels}
    out_deg = {lb: 0 for lb in labels}
    adj = {lb: set() for lb in labels}

    for atom in atoms:
        for parent in atom.parents:
            if parent not in labels:
                continue
            out_deg[atom.label] += 1
            in_deg[parent] += 1
            adj[atom.label].add(parent)
            adj[parent].add(atom.label)

    seen: Set[str] = set()
    components: List[List[str]] = []
    for label in labels:
        if label in seen:
            continue
        stack = [label]
        seen.add(label)
        comp: List[str] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adj[cur]:
                if nxt in seen:
                    continue
                seen.add(nxt)
                stack.append(nxt)
        components.append(comp)
    components.sort(key=len, reverse=True)
    return in_deg, out_deg, components


def pick_component_representative(comp_labels: Sequence[str], by_label: Dict[str, Atom]) -> str:
    atoms = [by_label[x] for x in comp_labels if x in by_label]
    if not atoms:
        return comp_labels[0]
    statement_atoms = [a for a in atoms if a.atom_type in STATEMENT_TYPES]
    source = statement_atoms if statement_atoms else atoms
    source.sort(key=lambda a: kg_id_sort_key(a.kg_id))
    return source[0].label


def make_bridge_label(
    prefix: str,
    level: int,
    group_index: int,
    parents: Sequence[str],
    used: Set[str],
) -> str:
    seed = "|".join(parents).encode("utf-8")
    short = hashlib.sha256(seed).hexdigest()[:10]
    base = f"{prefix}-l{level:03d}-g{group_index:04d}-h{short}"
    label = base
    n = 2
    while label in used:
        label = f"{base}-v{n}"
        n += 1
    used.add(label)
    return label


def bridge_payload_tex(label: str, level: int, group_index: int, parents: Sequence[str]) -> str:
    short = hashlib.sha256(label.encode("utf-8")).hexdigest()[:12]
    preview = ", ".join(parents[:4]) + (" ..." if len(parents) > 4 else "")
    return (
        "% synthetic component bridge\n"
        f"% kg-label:{label}\n"
        f"% bridge-level:{level} group:{group_index}\n"
        f"% bridge-parents:{preview}\n"
        "\\phantomsection\n"
        f"\\label{{kgid:{short}}}\n"
        "\\paragraph{Component Bridge}\n"
        "\\textit{Synthetic bridge node for DAG connectivity.}\n"
    )


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    report_path = (
        args.report.resolve()
        if args.report
        else (kg_root / ".kgcache" / "visuals" / "dag_bridge_components_report.json")
    )
    max_parents = max(2, int(args.max_parents))

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        print("scan errors:")
        for err in scan_errors[:50]:
            print(f"- {err}")
        return 2
    if not atoms:
        print("No atoms found.")
        return 1

    by_label = {a.label: a for a in atoms}
    used_labels = set(by_label.keys())
    in_deg_before, out_deg_before, components_before = build_components(atoms)

    if len(components_before) <= 1:
        report = {
            "kg_root": str(kg_root),
            "apply": bool(args.apply),
            "status": "already_connected",
            "components_before": len(components_before),
            "components_after": len(components_before),
            "bridges_planned": 0,
            "bridges_created": 0,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report: {report_path}")
        print("Graph already weakly connected; no bridge added.")
        return 0

    rep_labels: List[str] = []
    for comp in components_before:
        rep_labels.append(pick_component_representative(comp, by_label))

    now = datetime.now(timezone.utc)
    next_kg_id = next_kg_id_factory(kg_root, now)
    atoms_dir = kg_root / "atoms"
    atoms_dir.mkdir(parents=True, exist_ok=True)

    bridge_plan: List[Dict[str, object]] = []
    current_labels = list(rep_labels)
    level = 0

    # K-ary merge tree over component representatives.
    while len(current_labels) > 1:
        next_labels: List[str] = []
        group_index = 0
        for start in range(0, len(current_labels), max_parents):
            group = current_labels[start : start + max_parents]
            if len(group) == 1:
                next_labels.append(group[0])
                continue
            label = make_bridge_label(args.prefix, level, group_index, group, used_labels)
            bridge_plan.append(
                {
                    "level": level,
                    "group_index": group_index,
                    "label": label,
                    "parents": list(group),
                }
            )
            next_labels.append(label)
            group_index += 1
        current_labels = next_labels
        level += 1

    bridges_created = 0
    if args.apply:
        for row in bridge_plan:
            label = str(row["label"])
            parents = [str(x) for x in row["parents"]]
            payload = bridge_payload_tex(label, int(row["level"]), int(row["group_index"]), parents)
            payload_bytes = payload.encode("utf-8")
            hash12 = hash12_for_bytes(payload_bytes)
            kg_id = next_kg_id()
            filename = f"{kg_id}__lbl-{label}__tp-note__h-{hash12}.tex"
            atom_path = atoms_dir / filename
            atom_path.write_bytes(payload_bytes)
            sidecar = atom_sidecar_path(atom_path)
            write_json(
                sidecar,
                {
                    "kg_id": kg_id,
                    "label": label,
                    "atom_type": "tp-note",
                    "parents": parents,
                    "parent_edges": [
                        {
                            "parent": parent,
                            "edge_type": "bridge_component",
                            "edge_source": "kg_bridge_components",
                            "edge_reason": "component_merge_tree",
                        }
                        for parent in parents
                    ],
                    "edge_schema_version": "v2",
                    "source_path": "",
                    "source_tex_label": "",
                    "canonical_label": label,
                    "task_id": "",
                    "task_kind": "synthetic_component_bridge",
                    "unit_env": "component_bridge",
                    "extractor_version": "bridge-components-v1",
                    "proof_orphan": False,
                    "bridge_level": int(row["level"]),
                    "bridge_group_index": int(row["group_index"]),
                },
            )
            bridges_created += 1

    atoms_after, scan_after = scan_atoms(kg_root, verify_hash=False)
    if scan_after:
        raise RuntimeError("scan after bridge failed:\n" + "\n".join(scan_after[:50]))
    in_deg_after, out_deg_after, components_after = build_components(atoms_after)

    report = {
        "kg_root": str(kg_root),
        "apply": bool(args.apply),
        "prefix": args.prefix,
        "max_parents": max_parents,
        "components_before": len(components_before),
        "components_after": len(components_after),
        "nodes_before": len(atoms),
        "nodes_after": len(atoms_after),
        "edges_before": int(sum(out_deg_before.values())),
        "edges_after": int(sum(out_deg_after.values())),
        "isolated_before": int(sum(1 for lb in in_deg_before if in_deg_before[lb] == 0 and out_deg_before[lb] == 0)),
        "isolated_after": int(sum(1 for lb in in_deg_after if in_deg_after[lb] == 0 and out_deg_after[lb] == 0)),
        "bridges_planned": len(bridge_plan),
        "bridges_created": bridges_created,
        "root_bridge_label": current_labels[0] if current_labels else "",
        "bridge_plan_sample": bridge_plan[:120],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"report: {report_path}")
    print(
        "components: "
        f"before={report['components_before']} after={report['components_after']} "
        f"bridges_planned={report['bridges_planned']} bridges_created={report['bridges_created']}"
    )
    print(
        "graph: "
        f"nodes {report['nodes_before']} -> {report['nodes_after']}, "
        f"edges {report['edges_before']} -> {report['edges_after']}, "
        f"isolated {report['isolated_before']} -> {report['isolated_after']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
