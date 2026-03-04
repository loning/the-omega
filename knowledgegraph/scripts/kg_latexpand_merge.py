#!/usr/bin/env python3
"""Merge a TeX project into one expanded .tex using latexpand."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from _kg_common import default_kg_root, ensure_dir

LATEXPAND_START_RE = re.compile(r"^\s*%+\s*start input\s+(.+?)\s*$")
LATEXPAND_END_RE = re.compile(r"^\s*%+\s*end input\s+(.+?)\s*$")
INPUT_MACROS = {"input", "include", "subfile"}
RESIDUAL_EXPAND_MAX_DEPTH = 64

try:
    from pylatexenc.latexwalker import LatexMacroNode, LatexWalker
except ImportError:
    LatexMacroNode = None
    LatexWalker = None


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


def _macro_first_braced_arg_text(node) -> str:
    if LatexMacroNode is None or not isinstance(node, LatexMacroNode):
        return ""
    if not node.nodeargd or not node.nodeargd.argnlist:
        return ""
    for arg in node.nodeargd.argnlist:
        if arg is None or not hasattr(arg, "latex_verbatim"):
            continue
        raw = arg.latex_verbatim().strip()
        if raw.startswith("{") and raw.endswith("}"):
            return raw[1:-1].strip()
    return ""


def _iter_nodes_recursive(nodes):
    for node in nodes or []:
        yield node
        if hasattr(node, "nodelist") and node.nodelist:
            yield from _iter_nodes_recursive(node.nodelist)
        if LatexMacroNode is not None and isinstance(node, LatexMacroNode) and node.nodeargd:
            for arg in node.nodeargd.argnlist:
                if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                    yield from _iter_nodes_recursive(arg.nodelist)


def find_input_macros(tex: str) -> List[Tuple[int, int, str]]:
    if LatexWalker is None:
        return []
    try:
        nodes, _, _ = LatexWalker(tex).get_latex_nodes(pos=0)
    except Exception:
        return []
    out: List[Tuple[int, int, str]] = []
    for node in _iter_nodes_recursive(nodes):
        if LatexMacroNode is None or not isinstance(node, LatexMacroNode):
            continue
        if node.macroname not in INPUT_MACROS:
            continue
        arg = _macro_first_braced_arg_text(node)
        if not arg:
            continue
        pos = int(getattr(node, "pos", -1))
        nlen = int(getattr(node, "len", -1))
        if pos < 0 or nlen <= 0:
            continue
        out.append((pos, pos + nlen, arg))
    out.sort(key=lambda item: item[0])
    return out


def resolve_input_path(
    raw_arg: str,
    *,
    base_dir: Path,
    fallback_dirs: Sequence[Path],
) -> Optional[Path]:
    token = raw_arg.strip()
    if not token:
        return None
    candidate = Path(token)
    trial_names = [candidate]
    if candidate.suffix == "":
        trial_names.append(Path(f"{token}.tex"))

    search_dirs: List[Path] = [base_dir.resolve()]
    for path in fallback_dirs:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved not in search_dirs:
            search_dirs.append(resolved)

    if candidate.is_absolute():
        for name in trial_names:
            path = name.resolve()
            if path.exists() and path.is_file():
                return path
        return None

    for root in search_dirs:
        for name in trial_names:
            path = (root / name).resolve()
            if path.exists() and path.is_file():
                return path
    return None


def source_path_for_pos(entries: Sequence[Dict[str, object]], pos: int, default: Path) -> Path:
    for rec in entries:
        try:
            start = int(rec.get("start", -1))
            end = int(rec.get("end", -1))
        except (TypeError, ValueError):
            continue
        if start <= pos < end:
            source = str(rec.get("path") or "").strip()
            if source:
                return Path(source).resolve()
            break
    return default.resolve()


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def expand_fragment_inputs_recursive(
    tex: str,
    *,
    source_path: Path,
    fallback_dirs: Sequence[Path],
    include_stack: Set[Path],
    depth: int = 0,
) -> Tuple[str, int, int]:
    if depth >= RESIDUAL_EXPAND_MAX_DEPTH:
        return tex, 0, 0
    macros = find_input_macros(tex)
    if not macros:
        return tex, 0, 0

    replaced = tex
    expanded_count = 0
    unresolved_count = 0

    for start, end, arg in reversed(macros):
        target = resolve_input_path(
            arg,
            base_dir=source_path.parent,
            fallback_dirs=fallback_dirs,
        )
        if target is None:
            unresolved_count += 1
            continue

        if target in include_stack:
            replacement = (
                f"% recursive input skipped {target.as_posix()}\n"
                f"\\input{{{arg}}}\n"
            )
            replaced = replaced[:start] + replacement + replaced[end:]
            continue

        try:
            child_tex = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unresolved_count += 1
            continue

        include_stack.add(target)
        expanded_child, child_count, child_unresolved = expand_fragment_inputs_recursive(
            child_tex,
            source_path=target,
            fallback_dirs=fallback_dirs,
            include_stack=include_stack,
            depth=depth + 1,
        )
        include_stack.remove(target)

        expanded_count += 1 + child_count
        unresolved_count += child_unresolved
        replacement = (
            f"% start input {target.as_posix()}\n"
            f"{_ensure_trailing_newline(expanded_child)}"
            f"% end input {target.as_posix()}\n"
        )
        replaced = replaced[:start] + replacement + replaced[end:]

    return replaced, expanded_count, unresolved_count


def expand_residual_inputs(
    expanded_tex: str,
    *,
    main_tex: Path,
) -> Tuple[str, int, int]:
    if LatexWalker is None:
        return expanded_tex, 0, 0

    entries = parse_latexpand_entries(expanded_tex, main_tex)
    macros = find_input_macros(expanded_tex)
    if not macros:
        return expanded_tex, 0, 0

    fallback_dirs: List[Path] = [main_tex.parent.resolve()]
    project_root = find_project_root(main_tex)
    if project_root is not None:
        fallback_dirs.append(project_root.resolve())

    replaced = expanded_tex
    expanded_count = 0
    unresolved_count = 0
    include_stack: Set[Path] = set()

    for start, end, arg in reversed(macros):
        source_path = source_path_for_pos(entries, start, main_tex)
        target = resolve_input_path(
            arg,
            base_dir=source_path.parent,
            fallback_dirs=fallback_dirs,
        )
        if target is None:
            unresolved_count += 1
            continue

        try:
            child_tex = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unresolved_count += 1
            continue

        include_stack.add(target)
        expanded_child, child_count, child_unresolved = expand_fragment_inputs_recursive(
            child_tex,
            source_path=target,
            fallback_dirs=fallback_dirs,
            include_stack=include_stack,
            depth=0,
        )
        include_stack.remove(target)

        replacement = (
            f"% start input {target.as_posix()}\n"
            f"{_ensure_trailing_newline(expanded_child)}"
            f"% end input {target.as_posix()}\n"
        )
        replaced = replaced[:start] + replacement + replaced[end:]
        expanded_count += 1 + child_count
        unresolved_count += child_unresolved

    return replaced, expanded_count, unresolved_count


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
    if explain:
        expanded_tex, residual_expanded, residual_unresolved = expand_residual_inputs(
            expanded_tex,
            main_tex=main_tex,
        )
        if residual_expanded > 0 or residual_unresolved > 0:
            print(
                "Residual input expansion:"
                f" expanded={residual_expanded}"
                f" unresolved={residual_unresolved}"
            )
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
