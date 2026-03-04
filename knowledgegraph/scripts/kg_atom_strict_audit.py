#!/usr/bin/env python3
"""Strict compliance audit for knowledgegraph atoms."""

from __future__ import annotations

import argparse
import json
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict per-atom compliance audit.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Output JSON path (default: <kg-root>/analysis_atom_strict_audit.json)",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=80,
        help="Max labels shown in sample lists",
    )
    parser.add_argument(
        "--require-proof-types",
        default="tp-def,tp-axiom,tp-lemma,tp-thm,tp-cor,tp-prop,tp-claim,tp-conj",
        help="Comma-separated atom types that must have proof support",
    )
    parser.add_argument(
        "--name-required-types",
        default="tp-def,tp-axiom,tp-lemma,tp-thm,tp-cor,tp-prop,tp-claim,tp-conj,tp-proof",
        help="Comma-separated atom types that must have meaningful name",
    )
    return parser.parse_args()


def parse_csv_types(raw: str) -> Set[str]:
    if not raw.strip():
        return set()
    return {tok.strip() for tok in raw.split(",") if tok.strip()}


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
    return any(looks_like_name_label(lb) for lb in labels)


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    output_json = (
        args.output_json.resolve()
        if args.output_json
        else (kg_root / "analysis_atom_strict_audit.json")
    )
    sample_limit = max(1, int(args.sample_limit))
    require_proof_types = parse_csv_types(args.require_proof_types)
    name_required_types = parse_csv_types(args.name_required_types)

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    by_label = {a.label: a for a in atoms}
    children_by_parent: Dict[str, List[str]] = defaultdict(list)
    for atom in atoms:
        for parent in atom.parents:
            if parent in by_label:
                children_by_parent[parent].append(atom.label)

    issues_by_code: Dict[str, List[str]] = defaultdict(list)
    fail_records: List[Dict[str, object]] = []
    pass_count = 0
    scoped_count = 0
    type_totals = Counter()
    type_failures = Counter()

    statement_labels = {a.label for a in atoms if a.atom_type in STATEMENT_TYPES}

    for atom in atoms:
        type_totals[atom.atom_type] += 1
        checks: List[str] = []
        atom_issues: List[str] = []

        meta = load_sidecar(atom.path)
        labels: Set[str] = set()
        if atom.ext == "tex":
            try:
                text = atom.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            labels, _, _ = extract_tex_crossrefs(text)

        if atom.atom_type in name_required_types:
            checks.append("name_required")
            if not has_meaningful_name(meta, labels):
                atom_issues.append("missing_meaningful_name")
                issues_by_code["missing_meaningful_name"].append(atom.label)

        if atom.atom_type in require_proof_types:
            checks.append("proof_required")
            proof_children = [
                child for child in children_by_parent.get(atom.label, [])
                if by_label.get(child) and by_label[child].atom_type in PROOF_TYPES
            ]
            if not proof_children:
                atom_issues.append("missing_proof_support")
                issues_by_code["missing_proof_support"].append(atom.label)

        if atom.atom_type in PROOF_TYPES:
            checks.append("proof_parent_required")
            statement_parents = [p for p in atom.parents if p in statement_labels]
            if not statement_parents:
                atom_issues.append("orphan_proof")
                issues_by_code["orphan_proof"].append(atom.label)

        if checks:
            scoped_count += 1
            if atom_issues:
                type_failures[atom.atom_type] += 1
                fail_records.append(
                    {
                        "label": atom.label,
                        "kg_id": atom.kg_id,
                        "atom_type": atom.atom_type,
                        "checks": checks,
                        "issues": atom_issues,
                        "parents": list(atom.parents),
                        "path": str(atom.path),
                    }
                )
            else:
                pass_count += 1

    fail_count = scoped_count - pass_count
    report = {
        "kg_root": str(kg_root),
        "scan_error_count": len(scan_errors),
        "scan_errors_sample": scan_errors[:sample_limit],
        "rule_config": {
            "name_required_types": sorted(name_required_types),
            "require_proof_types": sorted(require_proof_types),
        },
        "summary": {
            "atom_total": len(atoms),
            "scoped_atom_total": scoped_count,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": round((pass_count / scoped_count), 6) if scoped_count else 0.0,
        },
        "issues": {
            code: {
                "count": len(labels),
                "sample": sorted(labels)[:sample_limit],
            }
            for code, labels in sorted(issues_by_code.items())
        },
        "per_type": {
            atom_type: {
                "total": type_totals[atom_type],
                "fail": type_failures[atom_type],
                "pass": type_totals[atom_type] - type_failures[atom_type],
            }
            for atom_type in sorted(type_totals.keys())
        },
        "failing_atoms_sample": fail_records[:sample_limit],
    }

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"strict audit report: {output_json}")
    print(
        f"scoped={report['summary']['scoped_atom_total']} "
        f"pass={report['summary']['pass_count']} "
        f"fail={report['summary']['fail_count']} "
        f"pass_rate={report['summary']['pass_rate']:.4f}"
    )
    if report["issues"]:
        print("issue_counts:")
        for code, payload in report["issues"].items():
            print(f"  {code}: {payload['count']}")
    else:
        print("issue_counts: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
