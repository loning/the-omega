#!/usr/bin/env python3
"""Merge a TeX project into one expanded .tex using latexpand."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List

from _kg_common import default_kg_root, ensure_dir

LATEXPAND_START_RE = re.compile(r"^\s*%+\s*start input\s+(.+?)\s*$")
LATEXPAND_END_RE = re.compile(r"^\s*%+\s*end input\s+(.+?)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use latexpand to flatten a main TeX file into one merged file."
    )
    parser.add_argument("--main", type=Path, required=True, help="Path to main TeX file")
    parser.add_argument(
        "--kg-root",
        type=Path,
        default=None,
        help="Knowledgegraph root (used for default output path)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Merged output file path (default: <kg-root>/.kgcache/merged/<slug>.latexpanded.tex)",
    )
    parser.add_argument(
        "--map-output",
        type=Path,
        default=None,
        help="Optional JSON output for source segment map parsed from --explain markers",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="Timeout seconds for latexpand (0 means no timeout)",
    )
    parser.add_argument(
        "--no-explain",
        action="store_true",
        help="Disable --explain comments in merged output",
    )
    return parser.parse_args()


def find_project_root(main_tex: Path) -> Path | None:
    for parent in [main_tex.parent, *main_tex.parents]:
        if (parent / "sections").exists():
            return parent
    return None


def default_output_path(kg_root: Path, main_tex: Path) -> Path:
    safe_parts = [
        re.sub(r"[^A-Za-z0-9._-]+", "-", token).strip("-")
        for token in main_tex.resolve().parts[-6:]
    ]
    safe_parts = [p for p in safe_parts if p]
    suffix = "__".join(safe_parts) if safe_parts else "main-tex"
    return kg_root / ".kgcache" / "merged" / f"{suffix}.latexpanded.tex"


def parse_latexpand_entries(expanded_tex: str, main_tex: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    stack: List[str] = [main_tex.resolve().as_posix()]
    cursor = 0

    for line in expanded_tex.splitlines(keepends=True):
        start = cursor
        cursor += len(line)
        end = cursor

        stripped = line.rstrip("\r\n")
        m_start = LATEXPAND_START_RE.match(stripped)
        if m_start:
            rel = m_start.group(1).strip()
            inc = Path(rel)
            if not inc.is_absolute():
                inc = (main_tex.parent / inc).resolve()
            else:
                inc = inc.resolve()
            stack.append(inc.as_posix())
            continue

        m_end = LATEXPAND_END_RE.match(stripped)
        if m_end:
            if len(stack) > 1:
                stack.pop()
            continue

        source = stack[-1]
        if entries and entries[-1]["path"] == source and int(entries[-1]["end"]) == start:
            entries[-1]["end"] = end
        else:
            entries.append({"path": source, "start": start, "end": end})

    return entries


def run_latexpand(main_tex: Path, explain: bool, timeout: int) -> str:
    main_tex = main_tex.resolve()
    env = os.environ.copy()
    texinputs = env.get("TEXINPUTS", "")

    project_root = find_project_root(main_tex)
    search_dirs: List[str] = []
    for p in [main_tex.parent, project_root]:
        if p is None:
            continue
        token = p.resolve().as_posix() + "//"
        if token not in search_dirs:
            search_dirs.append(token)
    if search_dirs:
        prefix = ":".join(search_dirs)
        env["TEXINPUTS"] = f"{prefix}:{texinputs}" if texinputs else f"{prefix}:"

    cmd = ["latexpand", "--makeatletter", "-d", r"subfile=\input"]
    if explain:
        cmd.append("--explain")
    cmd.append(main_tex.name)

    try:
        proc = subprocess.run(
            cmd,
            cwd=main_tex.parent,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout if timeout > 0 else None,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"latexpand timeout after {timeout}s for {main_tex}"
        ) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        detail = stderr or stdout or "(no stderr/stdout)"
        raise RuntimeError(f"latexpand failed ({proc.returncode}) for {main_tex}: {detail}")

    return proc.stdout


def main() -> int:
    args = parse_args()
    main_tex = args.main.resolve()
    if not main_tex.exists() or not main_tex.is_file():
        print(f"main TeX not found: {main_tex}")
        return 2

    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    output_path = args.output.resolve() if args.output else default_output_path(kg_root, main_tex)
    ensure_dir(output_path.parent)

    explain = not args.no_explain
    expanded_tex = run_latexpand(main_tex, explain=explain, timeout=args.timeout)
    output_path.write_text(expanded_tex, encoding="utf-8")

    line_count = expanded_tex.count("\n") + (0 if expanded_tex.endswith("\n") else 1)
    print(f"Merged TeX written: {output_path}")
    print(f"Lines: {line_count}")

    if args.map_output:
        if not explain:
            print("map-output requested but --no-explain was set; skip map generation.")
        else:
            map_path = args.map_output.resolve()
            ensure_dir(map_path.parent)
            entries = parse_latexpand_entries(expanded_tex, main_tex)
            unique_sources = len({str(e["path"]) for e in entries})
            payload = {
                "main_tex": main_tex.as_posix(),
                "merged_tex": output_path.as_posix(),
                "entry_count": len(entries),
                "unique_source_count": unique_sources,
                "entries": entries,
            }
            map_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Source map written: {map_path}")
            print(f"Source segments: {len(entries)} (unique files: {unique_sources})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
