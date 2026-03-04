#!/usr/bin/env python3
"""Emit LLM task files from merged TeX knowledge units."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from _kg_common import (
    compact_label,
    default_kg_root,
    now_utc_compact,
    slugify,
)
try:
    from pylatexenc.latexwalker import (
        LatexCharsNode,
        LatexCommentNode,
        LatexEnvironmentNode,
        LatexMacroNode,
        LatexWalker,
    )
except ImportError:
    LatexCharsNode = None
    LatexCommentNode = None
    LatexEnvironmentNode = None
    LatexMacroNode = None
    LatexWalker = None

ENV_TO_TYPE = {
    "definition": "tp-def",
    "axiom": "tp-axiom",
    "lemma": "tp-lemma",
    "theorem": "tp-thm",
    "corollary": "tp-cor",
    "proposition": "tp-prop",
    "claim": "tp-claim",
    "conjecture": "tp-conj",
    "proof": "tp-proof",
    "example": "tp-exp",
    "remark": "tp-note",
    "algorithm": "tp-method",
    "equation": "tp-claim",
    "align": "tp-claim",
}

ENV_NAMES = sorted(ENV_TO_TYPE.keys(), key=len, reverse=True)
ANCHOR_ENV_TYPES = {k for k in ENV_TO_TYPE.keys() if k != "proof"}
EXTRACTOR_VERSION = "pylatexenc-top-level-v15-oversize-safe-recursive-gap-chunk"
VALID_LABEL_RE = re.compile(r"^[A-Za-z0-9:._/@+\-]+$")
MAX_UNIT_TEX_CHARS = 200_000
GAP_SPLIT_RE = re.compile(r"\n\s*\n+")
SUSPICIOUS_TARGET_ENV_CHARS = 300_000
GAP_STRUCTURAL_DROP_LINE_RE = re.compile(
    r"^\s*\\(?:"
    r"documentclass|usepackage|RequirePackage|"
    r"geometry|"
    r"newcommand|renewcommand|providecommand|DeclareMathOperator|"
    r"newtheorem|theoremstyle|"
    r"title|author|maketitle|tableofcontents|"
    r"makeatletter|makeatother|"
    r"tracinglostchars|hbadness|vbadness|hfuzz|"
    r"fvset|RecustomVerbatimEnvironment|BeforeBeginEnvironment|AfterEndEnvironment|"
    r"let|g@addto@macro|"
    r"input|include|subfile|"
    r"bibliography|bibliographystyle|"
    r"begin\{document\}|end\{document\}"
    r")(?=\b|\s|$)"
)
GAP_STRUCTURAL_DROP_WHOLE_LINE_RE = re.compile(r"^\s*\\(?:begingroup|endgroup)\b")
GAP_STRUCTURAL_DROP_CONTAINS = (
    r"\documentclass",
    r"\usepackage",
    r"\RequirePackage",
    r"\begin{document}",
    r"\end{document}",
    r"\input{",
    r"\include{",
    r"\subfile{",
    r"\bibliography{",
    r"\bibliographystyle",
)
GAP_PREAMBLE_MARKERS = (
    r"\documentclass",
    r"\usepackage",
    r"\maketitle",
    r"\tableofcontents",
    r"\begin{abstract}",
)
SECTIONING_CMD_RE = re.compile(r"\\(?:part|chapter|section|subsection|subsubsection)\*?\{")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit LLM tasks from merged TeX knowledge units.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--merged-tex",
        type=Path,
        required=True,
        help="Merged TeX file from kg_latexpand_merge.py (required)",
    )
    parser.add_argument(
        "--merged-map",
        type=Path,
        required=True,
        help="Merged source map JSON from kg_latexpand_merge.py (required)",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=0,
        help="Maximum tasks to emit in one run (0 means no limit)",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="Emit state file path "
        "(default: <kg-root>/.kgcache/merged/emit_state.json)",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Ignore previous emit state and emit all merged units",
    )
    return parser.parse_args()


def resolve_merged_paths(
    merged_tex_arg: Path,
    merged_map_arg: Path,
) -> tuple[Path, Path]:
    merged_tex = merged_tex_arg.resolve()
    merged_map = merged_map_arg.resolve()
    if not merged_tex.exists():
        raise RuntimeError(f"merged TeX does not exist: {merged_tex}")
    if not merged_map.exists():
        raise RuntimeError(f"merged map does not exist: {merged_map}")

    return merged_tex.resolve(), merged_map.resolve()


def load_merged_bundle(merged_tex_path: Path, merged_map_path: Path) -> tuple[str, List[Dict[str, object]]]:
    bundle_tex = read_full_text(merged_tex_path, max_chars=200_000_000)
    if not bundle_tex:
        raise RuntimeError(f"merged TeX is empty or unreadable: {merged_tex_path}")

    try:
        payload = json.loads(merged_map_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"failed reading merged map: {merged_map_path}: {exc}") from exc
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        raise RuntimeError(f"merged map missing entries list: {merged_map_path}")

    entries: List[Dict[str, object]] = []
    for idx, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("path") or "").strip()
        start = raw.get("start")
        end = raw.get("end")
        if not source:
            continue
        try:
            start_i = int(start)
            end_i = int(end)
        except (TypeError, ValueError):
            raise RuntimeError(f"invalid start/end in merged map entry #{idx}: {raw}") from None
        entries.append(
            {
                "path": Path(source).resolve().as_posix(),
                "start": start_i,
                "end": end_i,
            }
        )

    if not entries:
        raise RuntimeError(f"merged map has no usable entries: {merged_map_path}")
    entries.sort(key=lambda e: int(e["start"]))
    return bundle_tex, entries


def default_emit_state_path(kg_root: Path) -> Path:
    return kg_root / ".kgcache" / "merged" / "emit_state.json"


def load_emit_state(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_emit_state(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def hash_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unit_fingerprint(unit: Dict[str, object]) -> str:
    source_path = str(unit.get("source_path") or "")
    env = str(unit.get("env") or "")
    source_label = str(unit.get("source_label") or "")
    refs = ",".join(str(x) for x in (unit.get("source_refs") or []))
    unit_tex = str(unit.get("unit_tex") or "")
    raw = f"{source_path}\n{env}\n{source_label}\n{refs}\n{unit_tex}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def flatten_units(units_by_path: Dict[str, List[Dict[str, object]]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for source_path in sorted(units_by_path.keys()):
        units = units_by_path[source_path]
        sorted_units = sorted(
            units,
            key=lambda u: (
                str(u.get("canonical_label") or ""),
                str(u.get("env") or ""),
                hashlib.sha256(str(u.get("unit_tex") or "").encode("utf-8")).hexdigest()[:12],
            ),
        )
        out.extend(sorted_units)
    return out


def read_full_text(path: Path, max_chars: int = 2_000_000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:max_chars]


def split_ref_labels(raw: str) -> List[str]:
    out = []
    for part in raw.split(","):
        label = part.strip()
        if label:
            out.append(label)
    return out


def is_valid_tex_label(label: str) -> bool:
    if not label:
        return False
    if "#" in label or "\\" in label:
        return False
    if any(ch.isspace() for ch in label):
        return False
    return VALID_LABEL_RE.match(label) is not None


def unique_keep_order(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def strip_gap_structural_lines(chunk: str) -> tuple[str, bool]:
    """Drop TeX wrapper/preamble lines that should never become knowledge atoms."""
    dropped = False
    had_preamble_marker = any(token in chunk for token in GAP_PREAMBLE_MARKERS)
    kept: List[str] = []
    for line in chunk.splitlines():
        if GAP_STRUCTURAL_DROP_LINE_RE.match(line):
            dropped = True
            continue
        if GAP_STRUCTURAL_DROP_WHOLE_LINE_RE.match(line):
            dropped = True
            continue
        if any(token in line for token in GAP_STRUCTURAL_DROP_CONTAINS):
            dropped = True
            continue
        kept.append(line)
    out = "\n".join(kept).strip()
    if out and had_preamble_marker:
        m = SECTIONING_CMD_RE.search(out)
        if m is not None and m.start() > 0:
            out = out[m.start() :].lstrip()
            dropped = True
    if out:
        out += "\n"
    return out, dropped


def _is_latexpand_explain_comment(node) -> bool:
    if not LatexCommentNode or not isinstance(node, LatexCommentNode):
        return False
    comment = (node.comment or "").strip()
    return comment.startswith("start input ") or comment.startswith("end input ")


LTX_EXPLAIN_LINE_RE = re.compile(r"^\s*%\s*(?:start|end)\s+input\s+.+$")
LTX_VERB_START_RE = re.compile(r"^(?P<indent>\s*)\\verb\|%\s*start input\s+(?P<path>.+?)\s*$")
LTX_VERB_END_RE = re.compile(r"^\s*%\s*end input\s+.+$")


def normalize_latexpand_artifacts_fallback(tex: str) -> str:
    """Best-effort latexpand cleanup when pylatexenc is unavailable."""
    lines = tex.splitlines()
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = LTX_VERB_START_RE.match(line)
        if m:
            path = m.group("path").strip()
            end = i + 1
            while end < len(lines) and not LTX_VERB_END_RE.match(lines[end]):
                end += 1
            if end < len(lines):
                literal = f"\\input{{{path}}}"
                if "|" in literal:
                    literal = literal.replace("|", "/")
                out.append(f"{m.group('indent')}\\verb|{literal}|")
                i = end + 1
                continue

        if LTX_EXPLAIN_LINE_RE.match(line):
            i += 1
            continue

        out.append(line)
        i += 1

    if tex.endswith("\n"):
        return "\n".join(out) + "\n"
    return "\n".join(out)


def normalize_latexpand_artifacts_with_ast(tex: str) -> str:
    """Clean latexpand explain artifacts via AST edits (no TeX regex parsing)."""
    if LatexWalker is None:
        return normalize_latexpand_artifacts_fallback(tex)

    walker = LatexWalker(tex)
    root_nodes, _, _ = walker.get_latex_nodes(pos=0)
    edits: List[tuple[int, int, str]] = []

    def recurse(nodes) -> None:
        if not nodes:
            return
        idx = 0
        while idx < len(nodes):
            node = nodes[idx]
            if _is_latexpand_explain_comment(node):
                edits.append((node.pos, node.pos + node.len, ""))
                idx += 1
                continue

            # latexpand known bug: \verb|\input{...}| may be expanded into
            # \verb|% start input ... <expanded body> % end input ...
            if (
                LatexMacroNode
                and LatexCharsNode
                and isinstance(node, LatexMacroNode)
                and node.macroname == "verb"
            ):
                verbatim_text = getattr(node.nodeargd, "verbatim_text", None) if node.nodeargd else None
                # Case A: latexpand bug produced giant verbatim payload that swallowed
                # expanded \input body; collapse back to literal \input text.
                if isinstance(verbatim_text, str):
                    stripped = verbatim_text.lstrip()
                    if stripped.startswith("% start input ") and "end input " in stripped:
                        first_line = stripped.splitlines()[0] if stripped.splitlines() else stripped
                        path = first_line[len("% start input ") :].strip()
                        literal = f"\\input{{{path}}}"
                        if "|" in literal:
                            literal = literal.replace("|", "/")
                        edits.append((node.pos, node.pos + node.len, f"\\verb|{literal}|"))
                        idx += 1
                        continue

                # Case B: parser could not parse \verb payload and left delimiter/body
                # as separate sibling nodes.
                if not node.nodeargd or verbatim_text is None:
                    if idx + 2 < len(nodes):
                        delim_node = nodes[idx + 1]
                        start_comment_node = nodes[idx + 2]
                        if (
                            isinstance(delim_node, LatexCharsNode)
                            and delim_node.chars.startswith("|")
                            and isinstance(start_comment_node, LatexCommentNode)
                        ):
                            start_comment = (start_comment_node.comment or "").strip()
                            if start_comment.startswith("start input "):
                                path = start_comment[len("start input ") :].strip()
                                end_idx = idx + 2
                                while end_idx + 1 < len(nodes):
                                    end_idx += 1
                                    end_node = nodes[end_idx]
                                    if (
                                        isinstance(end_node, LatexCommentNode)
                                        and (end_node.comment or "").strip().startswith("end input ")
                                    ):
                                        break
                                end_pos = nodes[end_idx].pos + nodes[end_idx].len
                                literal = f"\\input{{{path}}}"
                                if "|" in literal:
                                    literal = literal.replace("|", "/")
                                edits.append((node.pos, end_pos, f"\\verb|{literal}|"))
                                idx = end_idx + 1
                                continue

            if hasattr(node, "nodelist") and node.nodelist:
                recurse(node.nodelist)
            if LatexMacroNode and isinstance(node, LatexMacroNode) and node.nodeargd:
                for arg in node.nodeargd.argnlist:
                    if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                        recurse(arg.nodelist)
            idx += 1

    recurse(root_nodes)
    if not edits:
        return tex

    out = tex
    for start, end, repl in sorted(edits, key=lambda x: (x[0], x[1]), reverse=True):
        if start < 0 or end < start or end > len(out):
            continue
        out = out[:start] + repl + out[end:]
    return out


def _macro_first_arg_text(node) -> str:
    if not LatexMacroNode or not isinstance(node, LatexMacroNode):
        return ""
    if not node.nodeargd or not node.nodeargd.argnlist:
        return ""
    arg0 = node.nodeargd.argnlist[0]
    if arg0 is None or not hasattr(arg0, "latex_verbatim"):
        return ""
    text = arg0.latex_verbatim()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    return text.strip()


def _iter_nodes_recursive(nodes, *, skip_nested_target_envs: bool = False):
    for node in nodes or []:
        yield node
        if LatexEnvironmentNode and isinstance(node, LatexEnvironmentNode):
            env_raw = node.environmentname or ""
            env_base = env_raw[:-1] if env_raw.endswith("*") else env_raw
            if skip_nested_target_envs and env_base in ENV_TO_TYPE:
                continue
        # Dive into normal child nodes.
        if hasattr(node, "nodelist") and node.nodelist:
            yield from _iter_nodes_recursive(
                node.nodelist, skip_nested_target_envs=skip_nested_target_envs
            )
        # Dive into macro arguments where refs/labels may appear.
        if LatexMacroNode and isinstance(node, LatexMacroNode) and node.nodeargd:
            for arg in node.nodeargd.argnlist:
                if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                    yield from _iter_nodes_recursive(
                        arg.nodelist, skip_nested_target_envs=skip_nested_target_envs
                    )


def _collect_labels_refs(
    env_node, *, include_nested_target_envs: bool = False
) -> tuple[List[str], List[str]]:
    labels: List[str] = []
    refs: List[str] = []
    for node in _iter_nodes_recursive(
        getattr(env_node, "nodelist", None), skip_nested_target_envs=not include_nested_target_envs
    ):
        if not LatexMacroNode or not isinstance(node, LatexMacroNode):
            continue
        macro = node.macroname
        arg = _macro_first_arg_text(node)
        if not arg:
            continue
        if macro == "label":
            if is_valid_tex_label(arg):
                labels.append(arg)
        elif macro in {"ref", "eqref", "autoref", "cref", "Cref"}:
            refs.extend([x for x in split_ref_labels(arg) if is_valid_tex_label(x)])
    return unique_keep_order(labels), unique_keep_order(refs)


def _collect_labels_refs_from_fragment(tex_fragment: str) -> tuple[List[str], List[str]]:
    if not tex_fragment.strip():
        return [], []
    try:
        walker = LatexWalker(tex_fragment)
        nodes, _, _ = walker.get_latex_nodes(pos=0)
    except Exception:
        return [], []
    holder = type("NodeHolder", (), {"nodelist": nodes})()
    return _collect_labels_refs(holder, include_nested_target_envs=True)


def _clean_gap_text(tex_fragment: str) -> str:
    lines: List[str] = []
    for line in tex_fragment.splitlines():
        if line.lstrip().startswith("%"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _node_verbatim_slice(tex: str, node) -> str:
    pos = getattr(node, "pos", None)
    nlen = getattr(node, "len", None)
    if isinstance(pos, int) and isinstance(nlen, int) and pos >= 0 and nlen >= 0:
        end = pos + nlen
        if end <= len(tex):
            return tex[pos:end]
    if hasattr(node, "latex_verbatim"):
        try:
            return node.latex_verbatim()
        except Exception:
            return ""
    return ""


def _split_large_text_fragments(text: str, *, max_chars: int) -> List[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    chunks: List[str] = []
    cursor = 0
    while cursor < len(cleaned):
        upper = min(len(cleaned), cursor + max_chars)
        if upper < len(cleaned):
            cut = cleaned.rfind("\n\n", cursor, upper)
            if cut <= cursor:
                cut = cleaned.rfind("\n", cursor, upper)
            if cut <= cursor:
                cut = upper
        else:
            cut = upper
        piece = cleaned[cursor:cut].strip()
        if piece:
            chunks.append(piece + "\n")
        cursor = cut
        while cursor < len(cleaned) and cleaned[cursor].isspace():
            cursor += 1
    return chunks


def _chunk_gap_text(tex_fragment: str, *, max_chars: int = 80_000) -> List[str]:
    cleaned = _clean_gap_text(tex_fragment)
    if not cleaned:
        return []
    if LatexWalker is None:
        return _split_large_text_fragments(cleaned, max_chars=max_chars)
    try:
        walker = LatexWalker(cleaned)
        nodes, _, _ = walker.get_latex_nodes(pos=0)
    except Exception:
        return _split_large_text_fragments(cleaned, max_chars=max_chars)

    chunks: List[str] = []
    current_parts: List[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_len
        if not current_parts:
            return
        merged = "".join(current_parts).strip()
        if merged:
            chunks.append(merged + "\n")
        current_parts.clear()
        current_len = 0

    for node in nodes:
        part = _node_verbatim_slice(cleaned, node)
        if not part:
            continue
        if len(part) > max_chars:
            flush()
            chunks.extend(_split_large_text_fragments(part, max_chars=max_chars))
            continue
        if current_len + len(part) > max_chars and current_parts:
            flush()
        current_parts.append(part)
        current_len += len(part)

    flush()
    return [c for c in chunks if c.strip()]


def _iter_top_level_target_environment_nodes(nodes, *, in_target_env: bool = False):
    for node in nodes or []:
        is_env = LatexEnvironmentNode and isinstance(node, LatexEnvironmentNode)
        env_base = ""
        selected_as_top_level_target = False
        if is_env:
            env_raw = node.environmentname or ""
            env_base = env_raw[:-1] if env_raw.endswith("*") else env_raw
            is_target = env_base in ENV_TO_TYPE
            env_len = int(getattr(node, "len", 0) or 0)
            if is_target and not in_target_env and env_len <= SUSPICIOUS_TARGET_ENV_CHARS:
                yield node
                selected_as_top_level_target = True

        # Do not recurse into already-selected target envs; avoids nested duplication.
        child_in_target = in_target_env or selected_as_top_level_target
        if selected_as_top_level_target:
            continue

        if hasattr(node, "nodelist") and node.nodelist:
            yield from _iter_top_level_target_environment_nodes(
                node.nodelist, in_target_env=child_in_target
            )
        if LatexMacroNode and isinstance(node, LatexMacroNode) and node.nodeargd:
            for arg in node.nodeargd.argnlist:
                if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                    yield from _iter_top_level_target_environment_nodes(
                        arg.nodelist, in_target_env=child_in_target
                    )


def _env_needs_verb_payload_repair(env_node) -> bool:
    for node in _iter_nodes_recursive(getattr(env_node, "nodelist", None)):
        if not LatexMacroNode or not isinstance(node, LatexMacroNode):
            continue
        if node.macroname != "verb":
            continue
        if not node.nodeargd:
            return True
        verbatim_text = getattr(node.nodeargd, "verbatim_text", None)
        if isinstance(verbatim_text, str) and verbatim_text.lstrip().startswith("% start input "):
            return True
    return False


def extract_tex_knowledge_units(
    tex: str,
    source_stem: str,
    *,
    include_label_anchors: bool = False,
) -> List[Dict[str, object]]:
    if LatexWalker is None:
        raise RuntimeError(
            "pylatexenc is required for TeX atom extraction. "
            "Install with: python3 -m pip install --user --break-system-packages pylatexenc"
        )

    walker = LatexWalker(tex)
    root_nodes, _, _ = walker.get_latex_nodes(pos=0)
    units: List[Dict[str, object]] = []

    env_nodes = sorted(
        list(_iter_top_level_target_environment_nodes(root_nodes)),
        key=lambda node: getattr(node, "pos", 0),
    )
    last_anchor_ref = ""
    covered_labels: set[str] = set()
    env_ranges: List[tuple[int, int]] = []
    for env_node in env_nodes:
        env_raw = env_node.environmentname or ""
        env_base = env_raw[:-1] if env_raw.endswith("*") else env_raw
        if env_base not in ENV_TO_TYPE:
            continue

        block = tex[env_node.pos : env_node.pos + env_node.len]
        block = normalize_latexpand_artifacts_with_ast(block)
        env_ranges.append((env_node.pos, env_node.pos + env_node.len))
        labels, refs = _collect_labels_refs(env_node, include_nested_target_envs=False)
        covered_labels_nested, _ = _collect_labels_refs(env_node, include_nested_target_envs=True)
        covered_labels.update(covered_labels_nested)
        source_label = labels[0] if labels else ""
        canonical = compact_label(
            slugify(source_label)
            if source_label
            else slugify(f"{source_stem}-{env_base}-{len(units) + 1:04d}")
        )
        if env_base == "proof":
            if not refs and last_anchor_ref:
                refs = [last_anchor_ref]
            # Drop orphan proofs: proof atoms must be attached to a statement atom.
            if not refs:
                continue
        payload_normalizer_version = "tex-verb-sanitize-v1" if _env_needs_verb_payload_repair(env_node) else ""
        units.append(
                {
                    "env": env_base,
                    "node_type": ENV_TO_TYPE[env_base],
                    "source_label": source_label,
                    "canonical_label": canonical,
                    "source_refs": refs,
                    "unit_tex": block,
                    "span_start": int(env_node.pos),
                    "payload_normalizer_version": payload_normalizer_version,
                }
            )
        if env_base in ANCHOR_ENV_TYPES:
            last_anchor_ref = source_label or canonical

    gap_unit_index = 0

    def append_gap_units(raw_gap: str, gap_start_pos: int) -> None:
        nonlocal gap_unit_index, last_anchor_ref
        for chunk in _chunk_gap_text(raw_gap):
            if not chunk.strip():
                continue
            chunk = normalize_latexpand_artifacts_with_ast(chunk)
            chunk, dropped_structural = strip_gap_structural_lines(chunk)
            if not chunk.strip():
                continue
            labels, refs = _collect_labels_refs_from_fragment(chunk)
            covered_labels.update(labels)
            source_label = labels[0] if labels else ""
            gap_unit_index += 1
            canonical = compact_label(
                slugify(source_label)
                if source_label
                else slugify(f"{source_stem}-gap-{gap_unit_index:04d}")
            )
            source_refs = unique_keep_order(refs)
            if not source_refs and last_anchor_ref:
                source_refs = [last_anchor_ref]
            payload_normalizer_version = "gap-structural-strip-v1" if dropped_structural else ""
            units.append(
                {
                    "env": "gap_note",
                    "node_type": "tp-note",
                    "source_label": source_label,
                    "canonical_label": canonical,
                    "source_refs": source_refs,
                    "unit_tex": chunk,
                    "span_start": int(gap_start_pos),
                    "payload_normalizer_version": payload_normalizer_version,
                }
            )
            if source_label:
                last_anchor_ref = source_label

    cursor = 0
    for start, end in sorted(env_ranges, key=lambda x: x[0]):
        if start > cursor:
            append_gap_units(tex[cursor:start], cursor)
        if end > cursor:
            cursor = end
    if cursor < len(tex):
        append_gap_units(tex[cursor:], cursor)

    if include_label_anchors:
        anchor_seen: set[str] = set()
        for node in _iter_nodes_recursive(root_nodes):
            if not LatexMacroNode or not isinstance(node, LatexMacroNode):
                continue
            if node.macroname != "label":
                continue
            label = _macro_first_arg_text(node)
            if not label or not is_valid_tex_label(label):
                continue
            if label in covered_labels:
                continue
            if label in anchor_seen:
                continue
            anchor_seen.add(label)
            canonical = compact_label(slugify(label) if label else slugify(f"{source_stem}-label-anchor"))
            units.append(
                {
                    "env": "label_anchor",
                    "node_type": "tp-note",
                    "source_label": label,
                    "canonical_label": canonical,
                    "source_refs": [],
                    "unit_tex": f"\\label{{{label}}}\n",
                    "span_start": int(getattr(node, "pos", 0)),
                }
            )

    return units


def build_tex_bundle(tex_paths: List[Path]) -> tuple[str, List[Dict[str, object]]]:
    parts: List[str] = []
    entries: List[Dict[str, object]] = []
    cursor = 0

    for path in tex_paths:
        resolved = path.resolve()
        header = f"% KG_BUNDLE_FILE_BEGIN {resolved.as_posix()}\n"
        parts.append(header)
        cursor += len(header)

        text = read_full_text(resolved)
        start = cursor
        parts.append(text)
        cursor += len(text)
        if not text.endswith("\n"):
            parts.append("\n")
            cursor += 1
        end = cursor

        footer = f"% KG_BUNDLE_FILE_END {resolved.as_posix()}\n"
        parts.append(footer)
        cursor += len(footer)

        entries.append(
            {
                "path": str(resolved),
                "start": start,
                "end": end,
            }
        )

    return "".join(parts), entries


def enforce_merged_only_unit_limits(
    units: List[Dict[str, object]],
    *,
    max_unit_tex_chars: int = MAX_UNIT_TEX_CHARS,
) -> tuple[List[Dict[str, object]], Dict[str, int]]:
    out: List[Dict[str, object]] = []
    stats = {"oversized_dropped": 0, "oversized_split": 0, "oversized_kept": 0}
    for unit in units:
        unit_tex = str(unit.get("unit_tex") or "")
        if len(unit_tex) > max_unit_tex_chars:
            env = str(unit.get("env") or "")
            if env in {"gap_note", "label_anchor"}:
                chunks = _chunk_gap_text(unit_tex, max_chars=max_unit_tex_chars)
                if not chunks:
                    stats["oversized_dropped"] += 1
                    continue
                base = compact_label(str(unit.get("canonical_label") or "gap"))
                for idx, chunk in enumerate(chunks, start=1):
                    sub = dict(unit)
                    sub["unit_tex"] = chunk
                    sub["canonical_label"] = compact_label(f"{base}-part-{idx:03d}")
                    if idx > 1:
                        sub["source_label"] = ""
                    out.append(sub)
                stats["oversized_split"] += 1
                continue
            stats["oversized_kept"] += 1
        out.append(unit)
    return out, stats


def build_units_index_from_bundle(
    bundle_tex: str,
    bundle_entries: List[Dict[str, object]],
) -> Dict[str, List[Dict[str, object]]]:
    # Parse the merged TeX as one coherent stream. Then map each extracted unit
    # back to its source file using merged-map position ranges.
    ranges: List[tuple[int, int, str]] = []
    for entry in sorted(bundle_entries, key=lambda e: int(e.get("start", 0))):
        try:
            start = int(entry.get("start", 0))
            end = int(entry.get("end", 0))
        except (TypeError, ValueError):
            continue
        if start < 0 or end <= start:
            continue
        source_path = Path(str(entry.get("path") or "")).resolve().as_posix()
        ranges.append((start, end, source_path))

    if not ranges:
        return {}

    units = extract_tex_knowledge_units(
        bundle_tex,
        "merged",
        include_label_anchors=True,
    )

    mapped_units: List[Dict[str, object]] = []
    ridx = 0
    for unit in units:
        pos = int(unit.get("span_start") or 0)
        while ridx + 1 < len(ranges) and pos >= ranges[ridx][1]:
            ridx += 1
        if ranges[ridx][0] <= pos < ranges[ridx][1]:
            source_path = ranges[ridx][2]
        else:
            source_path = ranges[-1][2]
            for start, end, path in ranges:
                if start <= pos < end:
                    source_path = path
                    break
        rec = dict(unit)
        rec["source_path"] = source_path
        mapped_units.append(rec)

    mapped_units, stats = enforce_merged_only_unit_limits(mapped_units)
    oversized_dropped_total = stats["oversized_dropped"]
    oversized_split_total = stats.get("oversized_split", 0)
    oversized_kept_total = stats.get("oversized_kept", 0)

    by_path_units: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    run_seen: set[str] = set()
    for unit in mapped_units:
        fp = unit_fingerprint(unit)
        if fp in run_seen:
            continue
        run_seen.add(fp)
        by_path_units[str(unit.get("source_path") or "")].append(unit)

    if oversized_dropped_total > 0 or oversized_split_total > 0 or oversized_kept_total > 0:
        print(
            "Strict merged-only audit: "
            f"oversized_dropped={oversized_dropped_total} "
            f"oversized_split={oversized_split_total} "
            f"oversized_kept={oversized_kept_total}"
        )

    return by_path_units


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

    try:
        merged_tex_path, merged_map_path = resolve_merged_paths(
            args.merged_tex,
            args.merged_map,
        )
        bundle_tex, bundle_entries = load_merged_bundle(merged_tex_path, merged_map_path)
        merged_units_by_path = build_units_index_from_bundle(bundle_tex, bundle_entries)
    except Exception as exc:
        print(f"Failed to load merged TeX bundle: {exc}")
        print(
            "Run kg_latexpand_merge.py first, then pass --merged-tex/--merged-map explicitly.\n"
            "Example merge:\n"
            "  python3 knowledgegraph/scripts/kg_latexpand_merge.py "
            "--kg-root knowledgegraph "
            "--main docs/papers/auric-golden-phi/"
            "2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/main.tex "
            "--output knowledgegraph/.kgcache/merged/grg_main.latexpanded.tex "
            "--map-output knowledgegraph/.kgcache/merged/grg_main.latexpanded.map.json\n"
            "Example emit:\n"
            "  python3 knowledgegraph/scripts/kg_emit_llm_tasks.py "
            "--kg-root knowledgegraph "
            "--merged-tex knowledgegraph/.kgcache/merged/grg_main.latexpanded.tex "
            "--merged-map knowledgegraph/.kgcache/merged/grg_main.latexpanded.map.json"
        )
        return 2

    merged_sha256 = hash_text_sha256(bundle_tex)
    all_units = flatten_units(merged_units_by_path)
    queue_dir = kg_root / ".kgcache" / "llm_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.state_file.resolve() if args.state_file else default_emit_state_path(kg_root)
    prior_state = {} if args.reset_state else load_emit_state(state_path)
    emitted_fingerprints = set(
        str(x)
        for x in (prior_state.get("emitted_unit_fingerprints") or [])
        if isinstance(x, str) and x
    )

    emitted = 0
    skipped_existing = 0
    ts = now_utc_compact()
    for uidx, unit in enumerate(all_units, start=1):
        if args.max_tasks > 0 and emitted >= args.max_tasks:
            break

        unit_fp = unit_fingerprint(unit)
        if unit_fp in emitted_fingerprints:
            skipped_existing += 1
            continue

        source_path = str(unit.get("source_path") or "")
        unit_hash = hashlib.sha256(str(unit["unit_tex"]).encode("utf-8")).hexdigest()[:12]
        unit_proposed = (
            f"{unit['canonical_label']}-{unit_hash}"
            if unit_hash
            else str(unit["canonical_label"])
        )
        payload_normalizer_version = str(unit.get("payload_normalizer_version") or "")
        if not payload_normalizer_version and str(unit.get("env") or "") == "proof":
            payload_normalizer_version = "proof-env-preserve-v1"
        task = {
            "task_id": f"TASK-{ts}-{emitted + 1:06d}",
            "created_at": ts,
            "source_name": "merged_tex",
            "change_type": "modified",
            "source_path": source_path,
            "old_hash": None,
            "new_hash": merged_sha256,
            "diff_excerpt": str(unit["unit_tex"])[:2000],
            "candidate_parent_labels": [slugify(r) for r in unit["source_refs"]],
            "suggested_node_type": unit["node_type"],
            "proposed_label": unit_proposed,
            "status": "pending",
            "task_kind": "tex_knowledge_unit",
            "unit_index": uidx,
            "unit_env": unit["env"],
            "canonical_label": unit["canonical_label"],
            "source_tex_label": unit["source_label"],
            "source_refs": unit["source_refs"],
            "unit_tex": unit["unit_tex"],
            "unit_fingerprint": unit_fp,
            "payload_normalizer_version": payload_normalizer_version,
            "merged_tex_path": str(merged_tex_path),
            "merged_map_path": str(merged_map_path),
            "merged_sha256": merged_sha256,
            "extractor_version": EXTRACTOR_VERSION,
        }
        task_path = queue_dir / f"task_{ts}_{emitted + 1:06d}.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        emitted_fingerprints.add(unit_fp)
        emitted += 1

    new_state = {
        "updated_at": ts,
        "merged_tex_path": str(merged_tex_path),
        "merged_map_path": str(merged_map_path),
        "merged_sha256": merged_sha256,
        "extractor_version": EXTRACTOR_VERSION,
        "unit_count": len(all_units),
        "emitted_unit_fingerprints": sorted(emitted_fingerprints),
    }
    write_emit_state(state_path, new_state)
    print(f"Merged units: {len(all_units)}")
    print(f"Skipped (already emitted): {skipped_existing}")
    print(f"Emitted {emitted} task(s) into {queue_dir}")
    print(f"State written: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
