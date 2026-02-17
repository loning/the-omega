#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strip auto-inserted timestamp comments from paper sources.

This repository occasionally accumulates comment lines that only record "added/modified"
timestamps (e.g. "日期与时间：2026-02-17 14:25:12" or "Time (Asia/Singapore): ...").
These lines are metadata and should not appear in the manuscript sources.

Policy implemented here:
  - Only remove full-line comments (LaTeX: '% ...', Python: '# ...').
  - Remove a line if (and only if) it looks like a timestamp record:
      * contains "日期与时间" or "当前时间", OR
      * contains an ISO date pattern (YYYY-MM-DD), with or without a time-of-day.
  - Do not touch non-comment content.

The script edits files in place and writes a small JSON report under:
  artifacts/export/strip_comment_timestamps_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class Change:
    path: str
    removed_lines: int


_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_CN_TIME_LABEL_RE = re.compile(r"(日期与时间|当前时间)")


def _iter_files(root: Path, include_dirs: Sequence[str], exts: Sequence[str]) -> Iterable[Path]:
    for rel in include_dirs:
        base = (root / rel).resolve()
        if not base.exists():
            continue
        if base.is_file():
            if base.suffix in exts:
                yield base
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in exts:
                continue
            yield p


def _comment_prefix_for_suffix(suffix: str) -> str | None:
    if suffix == ".tex":
        return "%"
    if suffix == ".py":
        return "#"
    return None


def _should_strip_comment_line(line: str) -> bool:
    if _CN_TIME_LABEL_RE.search(line):
        return True
    if _ISO_DATE_RE.search(line):
        return True
    return False


def _process_file(path: Path) -> Tuple[bool, int]:
    prefix = _comment_prefix_for_suffix(path.suffix)
    if prefix is None:
        return (False, 0)

    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    removed = 0
    out_lines: List[str] = []
    for ln in lines:
        s = ln.lstrip()
        if s.startswith(prefix) and _should_strip_comment_line(s):
            removed += 1
            continue
        out_lines.append(ln)

    if removed == 0:
        return (False, 0)

    new_text = "".join(out_lines)
    if new_text == original:
        return (False, 0)

    path.write_text(new_text, encoding="utf-8")
    return (True, removed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Strip timestamp-only comment lines.")
    parser.add_argument(
        "--root",
        type=str,
        default=str(Path(__file__).resolve().parent.parent),
        help="Paper root directory (defaults to scripts/..).",
    )
    parser.add_argument(
        "--include",
        type=str,
        nargs="*",
        default=["sections", "scripts"],
        help="Subdirectories under --root to scan.",
    )
    parser.add_argument(
        "--ext",
        type=str,
        nargs="*",
        default=[".tex", ".py"],
        help="File extensions to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only report what would change.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    include_dirs = list(args.include)
    exts = list(args.ext)

    print(f"[strip_timestamps] root={root}", flush=True)
    print(f"[strip_timestamps] include={include_dirs} ext={exts} dry_run={args.dry_run}", flush=True)

    t0 = time.time()
    last_progress = t0

    changed: List[Change] = []
    scanned = 0
    removed_total = 0

    paths = sorted(_iter_files(root, include_dirs=include_dirs, exts=exts))
    for p in paths:
        scanned += 1
        if (time.time() - last_progress) >= 20.0:
            print(
                f"[strip_timestamps] progress scanned={scanned}/{len(paths)} changed={len(changed)} removed_total={removed_total}",
                flush=True,
            )
            last_progress = time.time()

        if args.dry_run:
            prefix = _comment_prefix_for_suffix(p.suffix)
            if prefix is None:
                continue
            text = p.read_text(encoding="utf-8")
            removed = 0
            for ln in text.splitlines():
                s = ln.lstrip()
                if s.startswith(prefix) and _should_strip_comment_line(s):
                    removed += 1
            if removed > 0:
                changed.append(Change(path=str(p.relative_to(root)), removed_lines=removed))
                removed_total += removed
            continue

        did_change, removed = _process_file(p)
        if did_change:
            changed.append(Change(path=str(p.relative_to(root)), removed_lines=removed))
            removed_total += removed

    dt = time.time() - t0
    print(
        f"[strip_timestamps] done scanned={scanned} changed={len(changed)} removed_total={removed_total} elapsed_s={dt:.3f}",
        flush=True,
    )

    report_path = root / "artifacts" / "export" / "strip_comment_timestamps_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_payload: Dict[str, object] = {
        "root": str(root),
        "include": include_dirs,
        "ext": exts,
        "dry_run": bool(args.dry_run),
        "scanned_files": int(scanned),
        "changed_files": int(len(changed)),
        "removed_lines_total": int(removed_total),
        "changes": [c.__dict__ for c in changed],
        "elapsed_s": float(dt),
        "generated_at_unix_s": float(time.time()),
    }
    report_path.write_text(json.dumps(report_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[strip_timestamps] report={report_path}", flush=True)


if __name__ == "__main__":
    main()

