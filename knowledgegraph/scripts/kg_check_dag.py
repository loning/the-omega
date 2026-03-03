#!/usr/bin/env python3
"""Strict DAG check gate for atom graph."""

from __future__ import annotations

import argparse
from pathlib import Path

from _kg_common import default_kg_root, scan_atoms, validate_atoms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check atom DAG validity.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings as failures",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

    atoms, scan_errors = scan_atoms(kg_root)
    validation = validate_atoms(atoms)
    errors = list(scan_errors) + validation["errors"]
    warnings = validation["warnings"]

    print(f"Checked {len(atoms)} atoms")
    for err in errors:
        print(f"ERROR: {err}")
    for warn in warnings:
        print(f"WARN: {warn}")

    if errors:
        return 1
    if warnings and args.strict_warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
