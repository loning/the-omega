#!/usr/bin/env python3
"""Analyze LaTeX build logs for KG compile diagnostics."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from _kg_common import default_kg_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze KG LaTeX build logs.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--build-tag",
        default="index_book_grg",
        help="Build directory tag under .kgcache/build (default: index_book_grg)",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=None,
        help="Explicit log path (overrides --build-tag).",
    )
    parser.add_argument("--top", type=int, default=20, help="Top-N undefined refs/cites")
    return parser.parse_args()


def read_log(args: argparse.Namespace, kg_root: Path) -> tuple[Path, str]:
    if args.log_path:
        path = args.log_path.resolve()
    else:
        path = (kg_root / ".kgcache" / "build" / args.build_tag / "main.log").resolve()
    if not path.exists():
        raise FileNotFoundError(f"log not found: {path}")
    return path, path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    log_path, text = read_log(args, kg_root)

    counters = {
        "latex_error": len(re.findall(r"! LaTeX Error: ", text)),
        "missing_input": len(re.findall(r"missing input:", text)),
        "undefined_ref": len(re.findall(r"LaTeX Warning: Reference `", text)),
        "undefined_cite": len(re.findall(r"LaTeX Warning: Citation `", text)),
        "undefined_control": len(re.findall(r"! Undefined control sequence\\.", text)),
        "emergency_stop": len(re.findall(r"! Emergency stop\\.", text)),
        "runaway_argument": len(re.findall(r"Runaway argument\\?", text)),
        "overfull_hbox": len(re.findall(r"Overfull \\\\hbox", text)),
        "underfull_hbox": len(re.findall(r"Underfull \\\\hbox", text)),
    }

    refs = Counter(re.findall(r"LaTeX Warning: Reference `([^']+)' on page", text))
    cites = Counter(re.findall(r"LaTeX Warning: Citation `([^']+)'", text))

    print(f"log: {log_path}")
    for key in (
        "latex_error",
        "missing_input",
        "undefined_ref",
        "undefined_cite",
        "undefined_control",
        "emergency_stop",
        "runaway_argument",
        "overfull_hbox",
        "underfull_hbox",
    ):
        print(f"{key}={counters[key]}")

    if refs:
        print(f"top_undefined_refs (top={args.top}):")
        for name, count in refs.most_common(args.top):
            print(f"  {count:6d}  {name}")

    if cites:
        print(f"top_undefined_cites (top={args.top}):")
        for name, count in cites.most_common(args.top):
            print(f"  {count:6d}  {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
