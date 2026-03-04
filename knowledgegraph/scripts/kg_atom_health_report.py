#!/usr/bin/env python3
"""Analyze health metrics for knowledgegraph atom nodes."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Set

from _kg_common import atom_sidecar_path, default_kg_root, extract_tex_crossrefs, scan_atoms

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
NAMELESS_LABEL_PREFIXES: Sequence[str] = ("kgid:", "kg:")

BEGIN_ENV_RE = re.compile(r"\\begin\{([A-Za-z*@]+)\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze health metrics for atom nodes.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Output JSON path (default: <kg-root>/analysis_atom_health.json)",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=50,
        help="Maximum number of labels listed per issue category",
    )
    return parser.parse_args()


def load_sidecar(path: Path) -> Dict[str, object]:
    sidecar = atom_sidecar_path(path)
    if not sidecar.exists():
        return {}
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def looks_like_name_label(label: str) -> bool:
    token = label.strip()
    if not token:
        return False
    return not any(token.startswith(prefix) for prefix in NAMELESS_LABEL_PREFIXES)


def has_meaningful_name(meta: Dict[str, object], labels: Set[str]) -> bool:
    source_label = str(meta.get("source_tex_label") or "").strip()
    if looks_like_name_label(source_label):
        return True
    canonical = str(meta.get("canonical_label") or "").strip()
    if canonical:
        return True
    return any(looks_like_name_label(label) for label in labels)


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    output_json = args.output_json.resolve() if args.output_json else (kg_root / "analysis_atom_health.json")
    sample_limit = max(1, int(args.sample_limit))

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    by_label = {atom.label: atom for atom in atoms}

    children_by_parent: Dict[str, List[str]] = defaultdict(list)
    for atom in atoms:
        for parent in atom.parents:
            if parent in by_label:
                children_by_parent[parent].append(atom.label)

    type_counter = Counter(atom.atom_type for atom in atoms)
    ext_counter = Counter(atom.ext for atom in atoms)
    env_counter = Counter()

    name_ok_labels: Set[str] = set()
    statement_labels: Set[str] = set()
    proof_labels: Set[str] = set()
    orphan_proof_labels: List[str] = []

    for atom in atoms:
        if atom.atom_type in STATEMENT_TYPES:
            statement_labels.add(atom.label)
        if atom.atom_type in PROOF_TYPES:
            proof_labels.add(atom.label)

    proof_support_by_statement: Dict[str, List[str]] = defaultdict(list)

    for atom in atoms:
        if atom.ext != "tex":
            continue
        meta = load_sidecar(atom.path)
        text = atom.path.read_text(encoding="utf-8", errors="replace")
        labels, _, _ = extract_tex_crossrefs(text)
        if has_meaningful_name(meta, labels):
            name_ok_labels.add(atom.label)

        for env in BEGIN_ENV_RE.findall(text):
            env_counter[env] += 1

        if atom.label in proof_labels:
            statement_parents = [p for p in atom.parents if p in statement_labels]
            if not statement_parents:
                orphan_proof_labels.append(atom.label)
            for parent in statement_parents:
                proof_support_by_statement[parent].append(atom.label)

    missing_name_statements = sorted(
        label for label in statement_labels if label not in name_ok_labels
    )
    missing_proof_statements = sorted(
        label for label in statement_labels if not proof_support_by_statement.get(label)
    )
    missing_both_statements = sorted(
        label
        for label in statement_labels
        if label not in name_ok_labels and not proof_support_by_statement.get(label)
    )

    per_type = {}
    for atom_type in sorted(type_counter.keys()):
        labels_of_type = [a.label for a in atoms if a.atom_type == atom_type]
        labels_set = set(labels_of_type)
        if atom_type in STATEMENT_TYPES:
            with_name = sum(1 for lb in labels_of_type if lb in name_ok_labels)
            with_proof = sum(1 for lb in labels_of_type if proof_support_by_statement.get(lb))
            with_name_and_proof = sum(
                1
                for lb in labels_of_type
                if lb in name_ok_labels and proof_support_by_statement.get(lb)
            )
            per_type[atom_type] = {
                "count": len(labels_of_type),
                "with_name": with_name,
                "with_proof": with_proof,
                "with_name_and_proof": with_name_and_proof,
            }
        elif atom_type in PROOF_TYPES:
            with_statement_parent = sum(
                1 for lb in labels_of_type if lb not in set(orphan_proof_labels)
            )
            per_type[atom_type] = {
                "count": len(labels_of_type),
                "with_statement_parent": with_statement_parent,
                "orphan": len(labels_set) - with_statement_parent,
            }
        else:
            per_type[atom_type] = {"count": len(labels_of_type)}

    report = {
        "kg_root": str(kg_root),
        "scan_error_count": len(scan_errors),
        "scan_errors_sample": scan_errors[:sample_limit],
        "totals": {
            "atom_count": len(atoms),
            "tex_atom_count": sum(1 for a in atoms if a.ext == "tex"),
            "statement_atom_count": len(statement_labels),
            "proof_atom_count": len(proof_labels),
        },
        "coverage": {
            "statement_with_name": len(statement_labels) - len(missing_name_statements),
            "statement_with_proof": len(statement_labels) - len(missing_proof_statements),
            "statement_with_name_and_proof": len(statement_labels) - len(
                set(missing_name_statements) | set(missing_proof_statements)
            ),
            "proof_with_statement_parent": len(proof_labels) - len(orphan_proof_labels),
        },
        "issues": {
            "statement_missing_name_count": len(missing_name_statements),
            "statement_missing_proof_count": len(missing_proof_statements),
            "statement_missing_both_count": len(missing_both_statements),
            "orphan_proof_count": len(orphan_proof_labels),
            "statement_missing_name_sample": missing_name_statements[:sample_limit],
            "statement_missing_proof_sample": missing_proof_statements[:sample_limit],
            "statement_missing_both_sample": missing_both_statements[:sample_limit],
            "orphan_proof_sample": sorted(orphan_proof_labels)[:sample_limit],
        },
        "per_type": per_type,
        "counters": {
            "atom_type_count": dict(type_counter.most_common()),
            "ext_count": dict(ext_counter.most_common()),
            "tex_env_count_top100": dict(env_counter.most_common(100)),
        },
    }

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    totals = report["totals"]
    coverage = report["coverage"]
    issues = report["issues"]
    print(f"health report: {output_json}")
    print(f"atoms={totals['atom_count']} tex={totals['tex_atom_count']}")
    print(
        "statements="
        f"{totals['statement_atom_count']}, "
        f"with_name={coverage['statement_with_name']}, "
        f"with_proof={coverage['statement_with_proof']}, "
        f"with_name_and_proof={coverage['statement_with_name_and_proof']}"
    )
    print(
        "proofs="
        f"{totals['proof_atom_count']}, "
        f"with_statement_parent={coverage['proof_with_statement_parent']}, "
        f"orphan={issues['orphan_proof_count']}"
    )
    print(
        "issues: "
        f"missing_name={issues['statement_missing_name_count']}, "
        f"missing_proof={issues['statement_missing_proof_count']}, "
        f"missing_both={issues['statement_missing_both_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
