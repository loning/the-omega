#!/usr/bin/env python3
"""Scan atoms and optionally write cache outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _kg_common import (
    default_kg_root,
    ensure_dir,
    scan_atoms,
    topological_order,
    validate_atoms,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan atom files and validate format/hash.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--write-cache",
        action="store_true",
        help="Write scan cache into .kgcache/scan",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON summary to stdout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

    atoms, scan_errors = scan_atoms(kg_root)
    validation = validate_atoms(atoms)
    errors = list(scan_errors) + validation["errors"]
    warnings = validation["warnings"]

    ordered_labels = []
    if not errors:
        ordered_labels = [a.label for a in topological_order(atoms)]

    summary = {
        "kg_root": str(kg_root),
        "atom_count": len(atoms),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "topological_labels": ordered_labels,
    }

    if args.write_cache:
        cache_dir = kg_root / ".kgcache" / "scan"
        ensure_dir(cache_dir)
        write_json(cache_dir / "atoms.json", [a.to_dict() for a in atoms])
        write_json(cache_dir / "report.json", summary)
        edges = []
        for atom in atoms:
            for parent in atom.parents:
                edges.append({"child": atom.label, "parent": parent})
        write_json(cache_dir / "edges.json", edges)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"kg_root: {kg_root}")
        print(f"atoms: {len(atoms)}")
        print(f"errors: {len(errors)}")
        print(f"warnings: {len(warnings)}")
        for err in errors:
            print(f"ERROR: {err}")
        for warn in warnings:
            print(f"WARN: {warn}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
