#!/usr/bin/env python3
"""Repair isolated DAG atoms by inferring parent links from TeX refs and local order."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from _kg_common import (
    Atom,
    atom_sidecar_path,
    default_kg_root,
    extract_tex_crossrefs,
    normalize_parent_labels,
    now_utc_compact,
    parse_parent_edges,
    parse_parent_labels_from_meta,
    read_json,
    scan_atoms,
    slugify,
    write_json,
)

KG_ID_RE = re.compile(r"^KG-(?P<date>\d{8})-(?P<seq>\d+)$")
TASK_TAIL_RE = re.compile(r"-([0-9]{6,})$")
VERSIONED_LABEL_RE = re.compile(r"^(?P<canonical>[a-z0-9-]+)-h(?P<hash>[0-9a-f]{12})$")

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
PROOF_TYPES: Set[str] = {"tp-proof"}
TARGET_TYPES_DEFAULT: Set[str] = {
    "tp-proof",
    "tp-note",
    "tp-thm",
    "tp-prop",
    "tp-cor",
    "tp-claim",
    "tp-def",
    "tp-conj",
    "tp-lemma",
}
TARGET_ENVS_DEFAULT: Set[str] = {"proof", "gap_note", "remark", "label_anchor"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relink isolated atom nodes (parents=[])")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--apply", action="store_true", help="Write repaired parents to sidecar json")
    parser.add_argument(
        "--max-updates",
        type=int,
        default=1000000,
        help="Maximum number of nodes to relink",
    )
    parser.add_argument(
        "--target-types",
        default=",".join(sorted(TARGET_TYPES_DEFAULT)),
        help="Comma-separated atom types to consider for relink",
    )
    parser.add_argument(
        "--target-envs",
        default=",".join(sorted(TARGET_ENVS_DEFAULT)),
        help="Comma-separated unit_env to prioritize for relink",
    )
    parser.add_argument(
        "--neighbor-window",
        type=int,
        default=40,
        help="Backward search window in same source file",
    )
    parser.add_argument(
        "--max-parents",
        type=int,
        default=2,
        help="Maximum parent count to write per node",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Output report json path (default: <kg-root>/.kgcache/visuals/dag_relink_report.json)",
    )
    parser.add_argument(
        "--include-all-isolated",
        action="store_true",
        help="Ignore target-types/envs filters and attempt relink on all isolated tex nodes",
    )
    parser.add_argument(
        "--repair-orphan-proofs",
        action="store_true",
        help="Also repair proof atoms that lack statement parents (even if not isolated)",
    )
    parser.add_argument(
        "--allow-note-parent-note",
        action="store_true",
        help="Allow tp-note to attach to connected tp-note when no statement candidate is found",
    )
    parser.add_argument(
        "--global-anchor-fallback",
        action="store_true",
        help="Use global connected anchors when source-local candidates are unavailable",
    )
    return parser.parse_args()


def parse_csv_set(raw: str) -> Set[str]:
    return {tok.strip() for tok in raw.split(",") if tok.strip()}


def kg_id_sort_key(kg_id: str) -> Tuple[str, int]:
    m = KG_ID_RE.match(kg_id)
    if not m:
        return "", -1
    return m.group("date"), int(m.group("seq"))


def parse_task_seq(task_id: str) -> int:
    m = TASK_TAIL_RE.search(task_id.strip())
    if not m:
        return 10**12
    try:
        return int(m.group(1))
    except ValueError:
        return 10**12


def canonical_from_atom_label(label: str) -> str:
    m = VERSIONED_LABEL_RE.match(label)
    if not m:
        return label
    return m.group("canonical")


def load_reference_aliases(kg_root: Path) -> Dict[str, str]:
    alias_path = kg_root / "schema" / "reference_aliases.json"
    if not alias_path.exists():
        return {}
    try:
        payload = read_json(alias_path)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        return {}
    out: Dict[str, str] = {}
    for key, value in payload.items():
        src = str(key or "").strip()
        dst = str(value or "").strip()
        if src and dst:
            out[src] = dst
    return out


def normalize_label_alias_forms(label: str) -> Set[str]:
    value = label.strip()
    out = {value}
    if ":" in value:
        out.add(value.replace(":", "__"))
    if "__" in value:
        out.add(value.replace("__", ":"))
    return {x for x in out if x}


def load_meta_map(atoms: Sequence[Atom]) -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    for atom in atoms:
        sidecar = atom_sidecar_path(atom.path)
        if not sidecar.exists():
            out[atom.label] = {}
            continue
        try:
            payload = read_json(sidecar)
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        out[atom.label] = payload
    return out


def edge_map_by_parent(meta: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    for edge in parse_parent_edges(meta):
        parent = str(edge.get("parent") or "").strip()
        if not parent:
            continue
        row = dict(edge)
        row["parent"] = parent
        out[parent] = row
    return out


def build_in_out_degree(
    atoms: Sequence[Atom],
    parent_graph: Dict[str, List[str]],
) -> Tuple[Dict[str, int], Dict[str, int]]:
    labels = {a.label for a in atoms}
    in_deg = {lb: 0 for lb in labels}
    out_deg = {lb: 0 for lb in labels}
    for child, parents in parent_graph.items():
        out_deg[child] = len([p for p in parents if p in labels])
        for parent in parents:
            if parent in labels:
                in_deg[parent] += 1
    return in_deg, out_deg


def register_source_key(
    mapping: Dict[str, Tuple[str, str]],
    source_key: str,
    atom: Atom,
) -> None:
    key = source_key.strip()
    if not key:
        return
    candidates = set()
    for form in normalize_label_alias_forms(key):
        candidates.add(form)
        candidates.add(slugify(form))
    for item in candidates:
        if not item:
            continue
        prev = mapping.get(item)
        if prev is None or kg_id_sort_key(atom.kg_id) > kg_id_sort_key(prev[0]):
            mapping[item] = (atom.kg_id, atom.label)


def build_source_label_to_atom(
    atoms: Sequence[Atom],
    meta_map: Dict[str, Dict[str, object]],
) -> Dict[str, str]:
    mapping: Dict[str, Tuple[str, str]] = {}
    for atom in atoms:
        meta = meta_map.get(atom.label, {})
        source_tex_label = str(meta.get("source_tex_label") or "").strip()
        canonical_label = str(meta.get("canonical_label") or "").strip()
        if source_tex_label:
            register_source_key(mapping, source_tex_label, atom)
        if canonical_label:
            register_source_key(mapping, canonical_label, atom)
        register_source_key(mapping, canonical_from_atom_label(atom.label), atom)

        if atom.ext != "tex":
            continue
        try:
            text = atom.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        labels, _, _ = extract_tex_crossrefs(text)
        for source_label in labels:
            register_source_key(mapping, source_label, atom)

    return {k: v[1] for k, v in mapping.items()}


def resolve_ref_label(
    ref: str,
    source_label_to_atom: Dict[str, str],
    reference_aliases: Dict[str, str],
) -> Optional[str]:
    forms: List[str] = []
    for form in normalize_label_alias_forms(ref):
        forms.append(form)
        forms.append(slugify(form))

    for form in forms:
        target = source_label_to_atom.get(form)
        if target:
            return target

    alias_target = reference_aliases.get(ref)
    if alias_target:
        for form in normalize_label_alias_forms(alias_target):
            target = source_label_to_atom.get(form) or source_label_to_atom.get(slugify(form))
            if target:
                return target
    return None


def build_source_order(
    atoms: Sequence[Atom],
    meta_map: Dict[str, Dict[str, object]],
) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    by_source: Dict[str, List[Tuple[int, Tuple[str, int], str]]] = defaultdict(list)
    for atom in atoms:
        meta = meta_map.get(atom.label, {})
        source_path = str(meta.get("source_path") or "").strip()
        if not source_path:
            continue
        task_id = str(meta.get("task_id") or "")
        seq = parse_task_seq(task_id)
        by_source[source_path].append((seq, kg_id_sort_key(atom.kg_id), atom.label))

    ordered: Dict[str, List[str]] = {}
    position: Dict[str, int] = {}
    for source_path, rows in by_source.items():
        rows.sort(key=lambda x: (x[0], x[1], x[2]))
        labels = [lb for _, _, lb in rows]
        ordered[source_path] = labels
        for idx, lb in enumerate(labels):
            position[lb] = idx
    return ordered, position


def would_create_cycle(child: str, parent: str, parent_graph: Dict[str, List[str]]) -> bool:
    if child == parent:
        return True
    stack = [parent]
    seen: Set[str] = set()
    while stack:
        cur = stack.pop()
        if cur == child:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(parent_graph.get(cur, []))
    return False


def type_constraint_ok(child_type: str, parent_type: str) -> bool:
    if child_type in PROOF_TYPES and parent_type not in STATEMENT_TYPES:
        return False
    if child_type == "tp-def" and parent_type and parent_type != "tp-def":
        return False
    if child_type == "tp-note" and parent_type == "tp-note":
        return False
    if child_type == "tp-cor" and parent_type == "tp-cor":
        return False
    return True


def candidate_from_refs(
    atom: Atom,
    source_label_to_atom: Dict[str, str],
    reference_aliases: Dict[str, str],
    by_label: Dict[str, Atom],
) -> List[str]:
    if atom.ext != "tex":
        return []
    try:
        text = atom.path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    _, refs, _ = extract_tex_crossrefs(text)
    out: List[str] = []
    seen: Set[str] = set()
    for ref in refs:
        target = resolve_ref_label(ref, source_label_to_atom, reference_aliases)
        if not target or target == atom.label or target in seen:
            continue
        if target not in by_label:
            continue
        seen.add(target)
        out.append(target)
    return out


def candidate_from_neighbor(
    atom: Atom,
    meta: Dict[str, object],
    source_order: Dict[str, List[str]],
    source_pos: Dict[str, int],
    by_label: Dict[str, Atom],
    isolated_set: Set[str],
    *,
    window: int,
) -> List[str]:
    source_path = str(meta.get("source_path") or "").strip()
    if not source_path:
        return []
    labels = source_order.get(source_path)
    if not labels:
        return []
    pos = source_pos.get(atom.label)
    if pos is None:
        return []

    out_statement_connected: List[str] = []
    out_statement_any: List[str] = []
    out_note_connected: List[str] = []
    seen: Set[str] = set()
    lower = max(0, pos - max(1, window))
    upper = min(len(labels) - 1, pos + max(1, window))
    max_dist = max(pos - lower, upper - pos)

    for dist in range(1, max_dist + 1):
        for idx in (pos - dist, pos + dist):
            if idx < lower or idx > upper:
                continue
            candidate_label = labels[idx]
            if candidate_label == atom.label or candidate_label in seen:
                continue
            parent = by_label.get(candidate_label)
            if parent is None:
                continue
            seen.add(candidate_label)
            connected = candidate_label not in isolated_set
            if parent.atom_type in STATEMENT_TYPES:
                if connected:
                    out_statement_connected.append(candidate_label)
                else:
                    out_statement_any.append(candidate_label)
            elif parent.atom_type == "tp-note" and connected:
                out_note_connected.append(candidate_label)

    if atom.atom_type in PROOF_TYPES:
        return out_statement_connected + out_statement_any
    if atom.atom_type in STATEMENT_TYPES:
        return out_statement_connected + out_statement_any
    # note/other: prefer statement anchors, then connected notes.
    return out_statement_connected + out_statement_any + out_note_connected


def candidate_from_source_anchor(
    atom: Atom,
    meta: Dict[str, object],
    source_order: Dict[str, List[str]],
    source_pos: Dict[str, int],
    by_label: Dict[str, Atom],
    isolated_set: Set[str],
) -> List[str]:
    source_path = str(meta.get("source_path") or "").strip()
    if not source_path:
        return []
    labels = source_order.get(source_path)
    if not labels:
        return []
    pos = source_pos.get(atom.label)
    if pos is None:
        return []

    # 1) Earliest connected statement in same source file.
    for candidate_label in labels:
        if candidate_label == atom.label:
            continue
        if candidate_label in isolated_set:
            continue
        parent = by_label.get(candidate_label)
        if parent is None:
            continue
        if parent.atom_type in STATEMENT_TYPES:
            return [candidate_label]

    # 2) Earliest connected node in same source file.
    for candidate_label in labels:
        if candidate_label == atom.label:
            continue
        if candidate_label in isolated_set:
            continue
        if candidate_label in by_label:
            return [candidate_label]
    return []


def build_global_connected_pools(
    atoms: Sequence[Atom],
    isolated_set: Set[str],
) -> Dict[str, List[str]]:
    typed: Dict[str, List[Atom]] = defaultdict(list)
    for atom in atoms:
        if atom.label in isolated_set:
            continue
        typed[atom.atom_type].append(atom)
    out: Dict[str, List[str]] = {}
    for atom_type, items in typed.items():
        items_sorted = sorted(items, key=lambda a: kg_id_sort_key(a.kg_id))
        out[atom_type] = [a.label for a in items_sorted]
    return out


def candidate_from_global_anchor(
    atom: Atom,
    pools: Dict[str, List[str]],
) -> List[str]:
    preferred_types: List[str] = []
    if atom.atom_type in PROOF_TYPES:
        preferred_types = ["tp-thm", "tp-prop", "tp-lemma", "tp-claim", "tp-def", "tp-conj", "tp-cor"]
    elif atom.atom_type == "tp-def":
        preferred_types = ["tp-def"]
    elif atom.atom_type == "tp-cor":
        preferred_types = ["tp-thm", "tp-prop", "tp-lemma", "tp-claim", "tp-def"]
    elif atom.atom_type in {"tp-thm", "tp-prop", "tp-claim", "tp-conj", "tp-lemma"}:
        preferred_types = ["tp-thm", "tp-prop", "tp-lemma", "tp-claim", "tp-def", "tp-conj"]
    elif atom.atom_type == "tp-note":
        preferred_types = ["tp-thm", "tp-prop", "tp-lemma", "tp-claim", "tp-def", "tp-cor", "tp-conj", "tp-note"]
    else:
        preferred_types = ["tp-thm", "tp-prop", "tp-lemma", "tp-claim", "tp-def"]

    out: List[str] = []
    seen: Set[str] = set()
    for atom_type in preferred_types:
        labels = pools.get(atom_type, [])
        if not labels:
            continue
        for lb in reversed(labels[-6:]):  # latest connected anchors
            if lb == atom.label or lb in seen:
                continue
            seen.add(lb)
            out.append(lb)
    return out


def select_parents(
    atom: Atom,
    candidate_lists: Sequence[Tuple[str, List[str]]],
    by_label: Dict[str, Atom],
    parent_graph: Dict[str, List[str]],
    max_parents: int,
    allow_note_parent_note: bool,
) -> Tuple[List[str], List[str]]:
    selected: List[str] = []
    reasons: List[str] = []
    seen: Set[str] = set()

    for reason, candidates in candidate_lists:
        for parent_label in candidates:
            if len(selected) >= max(1, max_parents):
                break
            if parent_label in seen or parent_label == atom.label:
                continue
            parent_atom = by_label.get(parent_label)
            if parent_atom is None:
                continue
            if not type_constraint_ok(atom.atom_type, parent_atom.atom_type):
                if not (
                    allow_note_parent_note
                    and atom.atom_type == "tp-note"
                    and parent_atom.atom_type == "tp-note"
                ):
                    continue
            if atom.atom_type in PROOF_TYPES and parent_atom.atom_type not in STATEMENT_TYPES:
                continue
            if would_create_cycle(atom.label, parent_label, parent_graph):
                continue
            seen.add(parent_label)
            selected.append(parent_label)
            reasons.append(reason)
        if len(selected) >= max(1, max_parents):
            break
    return selected, reasons


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    report_path = (
        args.report.resolve()
        if args.report
        else (kg_root / ".kgcache" / "visuals" / "dag_relink_report.json")
    )
    target_types = parse_csv_set(args.target_types)
    target_envs = parse_csv_set(args.target_envs)

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        print("scan errors detected; abort:")
        for err in scan_errors[:50]:
            print(f"- {err}")
        return 2

    by_label = {a.label: a for a in atoms}
    meta_map = load_meta_map(atoms)
    parent_graph: Dict[str, List[str]] = {}
    for atom in atoms:
        meta = meta_map.get(atom.label, {})
        parent_graph[atom.label] = parse_parent_labels_from_meta(meta)

    in_deg_before, out_deg_before = build_in_out_degree(atoms, parent_graph)
    isolated_before = {
        label for label in by_label if in_deg_before[label] == 0 and out_deg_before[label] == 0
    }
    orphan_proofs_before = set()
    for atom in atoms:
        if atom.atom_type not in PROOF_TYPES:
            continue
        parents = parent_graph.get(atom.label, [])
        if not any(by_label.get(p) and by_label[p].atom_type in STATEMENT_TYPES for p in parents):
            orphan_proofs_before.add(atom.label)

    source_label_to_atom = build_source_label_to_atom(atoms, meta_map)
    reference_aliases = load_reference_aliases(kg_root)
    source_order, source_pos = build_source_order(atoms, meta_map)
    global_connected_pools = build_global_connected_pools(atoms, isolated_before)

    updates: List[Dict[str, object]] = []
    skipped_counts = Counter()
    reason_counts = Counter()

    repair_targets = set(isolated_before)
    if args.repair_orphan_proofs:
        repair_targets.update(orphan_proofs_before)

    for label in sorted(repair_targets):
        atom = by_label[label]
        if atom.ext != "tex":
            skipped_counts["non_tex"] += 1
            continue

        meta = meta_map.get(label, {})
        unit_env = str(meta.get("unit_env") or "").strip()
        proof_orphan = bool(meta.get("proof_orphan"))
        is_isolated = label in isolated_before
        is_orphan_proof = label in orphan_proofs_before

        if not args.include_all_isolated and is_isolated:
            if atom.atom_type not in target_types and unit_env not in target_envs and not proof_orphan:
                skipped_counts["filtered_by_target"] += 1
                continue

        refs_candidates = candidate_from_refs(atom, source_label_to_atom, reference_aliases, by_label)
        neighbor_candidates = candidate_from_neighbor(
            atom,
            meta,
            source_order,
            source_pos,
            by_label,
            isolated_before,
            window=max(1, args.neighbor_window),
        )
        source_anchor_candidates = candidate_from_source_anchor(
            atom,
            meta,
            source_order,
            source_pos,
            by_label,
            isolated_before,
        )
        global_anchor_candidates: List[str] = []
        if args.global_anchor_fallback:
            global_anchor_candidates = candidate_from_global_anchor(atom, global_connected_pools)

        selected, picked_reasons = select_parents(
            atom,
            [
                ("refs", refs_candidates),
                ("neighbor_backtrack", neighbor_candidates),
                ("source_anchor", source_anchor_candidates),
                ("global_anchor", global_anchor_candidates),
            ],
            by_label,
            parent_graph,
            max_parents=max(1, args.max_parents),
            allow_note_parent_note=bool(args.allow_note_parent_note),
        )

        if not selected:
            skipped_counts["no_candidate"] += 1
            continue

        selected_reason_map: Dict[str, str] = {}
        for idx, parent in enumerate(selected):
            if idx < len(picked_reasons):
                selected_reason_map[parent] = picked_reasons[idx]
            else:
                selected_reason_map[parent] = "relink"

        old_parents = list(parent_graph.get(label, []))
        merged_parents: List[str] = []
        max_parents = max(1, args.max_parents)
        if is_orphan_proof:
            # Preserve existing proof context edges first, then append at least one
            # statement parent if possible.
            for parent in old_parents:
                if len(merged_parents) >= max_parents:
                    break
                if parent in merged_parents or parent not in by_label:
                    continue
                if would_create_cycle(label, parent, parent_graph):
                    continue
                merged_parents.append(parent)

            for parent in selected:
                if parent in merged_parents or parent not in by_label:
                    continue
                if len(merged_parents) >= max_parents:
                    break
                if would_create_cycle(label, parent, parent_graph):
                    continue
                merged_parents.append(parent)

            has_statement_parent = any(
                by_label.get(p) and by_label[p].atom_type in STATEMENT_TYPES
                for p in merged_parents
            )
            if not has_statement_parent:
                for parent in selected:
                    if parent not in by_label:
                        continue
                    if by_label[parent].atom_type not in STATEMENT_TYPES:
                        continue
                    if would_create_cycle(label, parent, parent_graph):
                        continue
                    # If full, replace one non-statement slot.
                    if len(merged_parents) >= max_parents:
                        replaced = False
                        for idx, cur in enumerate(merged_parents):
                            cur_atom = by_label.get(cur)
                            if cur_atom is None or cur_atom.atom_type in STATEMENT_TYPES:
                                continue
                            merged_parents[idx] = parent
                            replaced = True
                            break
                        if not replaced:
                            break
                    else:
                        merged_parents.append(parent)
                    break
        else:
            merged_parents = list(selected)

        merged_parents = normalize_parent_labels(merged_parents)

        updates.append(
            {
                "label": label,
                "kg_id": atom.kg_id,
                "atom_type": atom.atom_type,
                "unit_env": unit_env,
                "target_kind": "orphan_proof" if is_orphan_proof and not is_isolated else "isolated",
                "old_parents": old_parents,
                "new_parents": merged_parents,
                "reasons": picked_reasons,
                "selected_reason_map": selected_reason_map,
                "source_path": str(meta.get("source_path") or ""),
            }
        )
        parent_graph[label] = list(merged_parents)
        for reason in picked_reasons:
            reason_counts[reason] += 1
        if len(updates) >= max(1, args.max_updates):
            skipped_counts["max_updates_reached"] += 1
            break

    applied = 0
    now = now_utc_compact()
    if args.apply:
        for row in updates:
            atom = by_label[row["label"]]
            sidecar = atom_sidecar_path(atom.path)
            payload = meta_map.get(atom.label, {}).copy()
            old_edge_map = edge_map_by_parent(payload)
            selected_map_raw = row.get("selected_reason_map")
            selected_map = selected_map_raw if isinstance(selected_map_raw, dict) else {}
            parent_edges: List[Dict[str, object]] = []
            for parent in normalize_parent_labels(row["new_parents"]):
                relink_reason = str(selected_map.get(parent) or "")
                if relink_reason:
                    parent_edges.append(
                        {
                            "parent": parent,
                            "edge_type": "relink",
                            "edge_source": "kg_relink_islands",
                            "edge_reason": relink_reason,
                        }
                    )
                    continue
                existing = old_edge_map.get(parent)
                if existing:
                    row_edge = dict(existing)
                    row_edge["parent"] = parent
                    parent_edges.append(row_edge)
                    continue
                parent_edges.append(
                    {
                        "parent": parent,
                        "edge_type": "relink_preserve",
                        "edge_source": "kg_relink_islands",
                        "edge_reason": "preserve_existing_parent",
                    }
                )

            payload["parents"] = normalize_parent_labels(row["new_parents"])
            payload["parent_edges"] = parent_edges
            payload["edge_schema_version"] = "v2"
            payload["relink_version"] = "relink-islands-v1"
            payload["relinked_at_utc"] = now
            payload["relink_reasons"] = row["reasons"]
            write_json(sidecar, payload)
            applied += 1

    in_deg_after, out_deg_after = build_in_out_degree(atoms, parent_graph)
    isolated_after = {
        label for label in by_label if in_deg_after[label] == 0 and out_deg_after[label] == 0
    }
    orphan_proofs_after = set()
    for atom in atoms:
        if atom.atom_type not in PROOF_TYPES:
            continue
        parents = parent_graph.get(atom.label, [])
        if not any(by_label.get(p) and by_label[p].atom_type in STATEMENT_TYPES for p in parents):
            orphan_proofs_after.add(atom.label)

    updates_by_type = Counter(row["atom_type"] for row in updates)
    updates_by_env = Counter(row["unit_env"] for row in updates)
    updates_by_target_kind = Counter(row.get("target_kind", "") for row in updates)

    report = {
        "kg_root": str(kg_root),
        "applied": bool(args.apply),
        "applied_count": applied,
        "max_updates": int(args.max_updates),
        "target_types": sorted(target_types),
        "target_envs": sorted(target_envs),
        "include_all_isolated": bool(args.include_all_isolated),
        "neighbor_window": int(args.neighbor_window),
        "max_parents": int(args.max_parents),
        "isolated_before": len(isolated_before),
        "isolated_after": len(isolated_after),
        "isolated_reduced": len(isolated_before) - len(isolated_after),
        "orphan_proofs_before": len(orphan_proofs_before),
        "orphan_proofs_after": len(orphan_proofs_after),
        "orphan_proofs_reduced": len(orphan_proofs_before) - len(orphan_proofs_after),
        "candidate_update_count": len(updates),
        "updates_by_type": dict(updates_by_type.most_common()),
        "updates_by_env": dict(updates_by_env.most_common()),
        "updates_by_target_kind": dict(updates_by_target_kind.most_common()),
        "picked_reason_counts": dict(reason_counts.most_common()),
        "skipped_counts": dict(skipped_counts.most_common()),
        "update_sample": updates[:200],
    }
    write_json(report_path, report)

    print(f"report: {report_path}")
    print(f"apply={args.apply} applied_count={applied} candidate_updates={len(updates)}")
    print(
        "isolated: "
        f"before={len(isolated_before)} after={len(isolated_after)} "
        f"reduced={len(isolated_before) - len(isolated_after)}"
    )
    print(
        "orphan_proofs: "
        f"before={len(orphan_proofs_before)} after={len(orphan_proofs_after)} "
        f"reduced={len(orphan_proofs_before) - len(orphan_proofs_after)}"
    )
    if updates_by_type:
        print("updates_by_type:")
        for k, v in updates_by_type.most_common(12):
            print(f"  {k}: {v}")
    if skipped_counts:
        print("skipped:")
        for k, v in skipped_counts.most_common(12):
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
