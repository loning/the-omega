#!/usr/bin/env python3
"""Compile audit/index/partial views into PDF using latexmk."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence, Set

from _kg_common import (
    ancestor_closure,
    atom_sidecar_path,
    default_kg_root,
    now_utc_compact,
    scan_atoms,
    tex_input_fragment_status,
    topological_order,
)

BEGIN_DOCUMENT_RE = re.compile(r"\\begin\s*\{\s*document\s*\}")
BIB_STYLE_LINE_RE = re.compile(r"^\s*\\bibliographystyle\{.+\}\s*$")
BIB_COMMAND_LINE_RE = re.compile(r"^\s*\\bibliography\{.+\}\s*$")
BIB_SUBFIX_ITEM_RE = re.compile(r"\\subfix\{([^{}]+)\}")
KGINPUT_LINE_RE = re.compile(r"^\s*\\kginput\{(?P<rel>atoms/KG-[^}]+\.tex)\}\s*$")
KGID_LABEL_LINE_RE = re.compile(r"^\s*\\label\{kgid:[^}]+\}\s*$")
REF_MACRO_WITH_ARG_RE = re.compile(
    r"\\(?P<cmd>ref|eqref|autoref|cref|Cref|pageref|vref|nameref)\{(?P<arg>[^{}]+)\}"
)
LIST_ENV_BEGIN_RE = re.compile(r"^\s*\\begin\{(?:itemize|enumerate|description)\}")
LIST_ENV_END_RE = re.compile(r"^\s*\\end\{(?:itemize|enumerate|description)\}")
ITEM_LINE_RE = re.compile(r"^\s*\\item(?:\s|$|\[)")
ENDINPUT_LINE_RE = re.compile(r"^\s*\\endinput(?:\s|%|$)")
LATEXPAND_ARTIFACT_LINE_RE = re.compile(
    r"^\s*%+\s*(?:start|end)\s+input\b|"
    r"\\%\s*(?:start|end)\s+input\b|"
    r"start\s+input\s+/Users/|"
    r"end\s+input\s+/Users/",
    re.IGNORECASE,
)
AUTO_ITEMIZE_CLOSE_HINT_RE = re.compile(
    r"^\s*\\(?:kgcloseproofifopen|part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\b|"
    r"^\s*\\begin\{(?:theorem|lemma|proposition|corollary|definition|remark|example|proof|conjecture|conclusion|algorithm|auditthm|auditcor|auditprop|auditlem)\}"
)
BEGIN_ENV_AT_RE = re.compile(r"\\begin\{([A-Za-z*@]+)\}")
END_ENV_AT_RE = re.compile(r"\\end\{([A-Za-z*@]+)\}")
BEGIN_END_RE = re.compile(r"\\(?P<kind>begin|end)\{(?P<env>[A-Za-z*@]+)\}")
DISPLAY_SCOPED_ENVS = {
    "aligned",
    "aligned*",
    "gathered",
    "gathered*",
    "split",
    "matrix",
    "pmatrix",
    "bmatrix",
    "Bmatrix",
    "vmatrix",
    "Vmatrix",
    "cases",
}
NON_MATHLIKE_RE = re.compile(r"[^\\s0-9A-Za-z\\\\{}_^&=,+*/().,:;|<>`~'\"!\\[\\]-]")


def repair_display_math_balance(text: str) -> str:
    """Repair unbalanced/nested display-math delimiters in fragment text.

    Handles common fragment damage patterns:
    - nested \\[ ... \\[ without closing prior display;
    - stray \\] or $$ toggles crossing delimiter styles.
    """
    out: List[str] = []
    mode: str | None = None  # None | "bracket" | "dollar" | "paren"
    display_env_stack: List[str] = []
    inline_paren_literal_depth = 0
    in_comment = False
    i = 0
    n = len(text)

    def close_active_display() -> None:
        nonlocal mode, inline_paren_literal_depth
        while display_env_stack:
            out.append(f"\\end{{{display_env_stack.pop()}}}")
        if mode == "bracket":
            out.append("\\]")
        elif mode == "dollar":
            out.append("$$")
        elif mode == "paren":
            out.append("\\)")
        mode = None
        inline_paren_literal_depth = 0

    while i < n:
        ch = text[i]

        if in_comment:
            out.append(ch)
            if ch == "\n":
                in_comment = False
            i += 1
            continue

        # TeX comments: ignore delimiter logic until newline.
        if ch == "%" and (i == 0 or text[i - 1] != "\\"):
            in_comment = True
            out.append(ch)
            i += 1
            continue

        begin_match = BEGIN_ENV_AT_RE.match(text, i)
        if begin_match:
            env_name = begin_match.group(1)
            token = begin_match.group(0)
            if mode is not None and env_name in DISPLAY_SCOPED_ENVS:
                display_env_stack.append(env_name)
            out.append(token)
            i = begin_match.end()
            continue

        end_match = END_ENV_AT_RE.match(text, i)
        if end_match:
            env_name = end_match.group(1)
            token = end_match.group(0)
            if mode is not None and display_env_stack and display_env_stack[-1] == env_name:
                display_env_stack.pop()
            out.append(token)
            i = end_match.end()
            continue

        if ch == "\\" and i + 1 < n and text[i + 1] == "[" and (i == 0 or text[i - 1] != "\\"):
            if mode is not None:
                close_active_display()
            mode = "bracket"
            out.append("\\[")
            i += 2
            continue

        if ch == "\\" and i + 1 < n and text[i + 1] == "]" and (i == 0 or text[i - 1] != "\\"):
            if mode == "bracket":
                close_active_display()
            elif mode == "dollar":
                # Close current $$ display first, then keep literal \].
                close_active_display()
                out.append("\\]")
            else:
                # Drop orphan \].
                pass
            i += 2
            continue

        if ch == "\\" and i + 1 < n and text[i + 1] == "(" and (i == 0 or text[i - 1] != "\\"):
            if mode is None:
                mode = "paren"
                out.append("\\(")
            elif mode == "paren":
                # Nested \( ... \) inside inline math is invalid.
                # Keep literal parenthesis content and preserve outer \(...\).
                out.append("(")
                inline_paren_literal_depth += 1
            else:
                # Nested \( ... \) inside existing math mode is invalid.
                # Keep literal parenthesis content instead.
                out.append("(")
            i += 2
            continue

        if ch == "\\" and i + 1 < n and text[i + 1] == ")" and (i == 0 or text[i - 1] != "\\"):
            if mode == "paren":
                if inline_paren_literal_depth > 0:
                    out.append(")")
                    inline_paren_literal_depth -= 1
                else:
                    close_active_display()
            elif mode in {"bracket", "dollar"}:
                out.append(")")
            else:
                # Drop orphan \).
                pass
            i += 2
            continue

        if ch == "$" and i + 1 < n and text[i + 1] == "$" and (i == 0 or text[i - 1] != "\\"):
            if mode is None:
                mode = "dollar"
                out.append("$$")
            elif mode == "dollar":
                close_active_display()
            else:
                # mode == "bracket": close \[...\] first, then open $$.
                close_active_display()
                mode = "dollar"
                out.append("$$")
            i += 2
            continue

        out.append(ch)
        i += 1

    if mode is not None:
        out.append("\n")
        close_active_display()
        out.append("\n")

    return "".join(out)


def close_display_before_non_math_text(text: str) -> str:
    """Close display/align blocks when prose leaked into math fragments."""
    out_lines: List[str] = []
    mode: str | None = None  # None | "bracket" | "dollar" | "paren"
    display_env_stack: List[str] = []

    def close_active() -> List[str]:
        nonlocal mode
        closers: List[str] = []
        while display_env_stack:
            closers.append(f"\\end{{{display_env_stack.pop()}}}")
        if mode == "bracket":
            closers.append("\\]")
        elif mode == "dollar":
            closers.append("$$")
        elif mode == "paren":
            closers.append("\\)")
        mode = None
        return closers

    def split_comment(line: str) -> str:
        for idx, ch in enumerate(line):
            if ch != "%":
                continue
            if idx > 0 and line[idx - 1] == "\\":
                continue
            return line[:idx]
        return line

    token_re = re.compile(
        r"\\begin\{([A-Za-z*@]+)\}|\\end\{([A-Za-z*@]+)\}|"
        r"(?<!\\)\\\[|(?<!\\)\\\]|(?<!\\)\\\(|(?<!\\)\\\)|(?<!\\)\$\$"
    )

    for line in text.splitlines():
        stripped = line.strip()

        # aligned-like environments cannot contain blank paragraphs.
        if mode is not None and display_env_stack and not stripped:
            continue

        if (
            mode is not None
            and display_env_stack
            and stripped
            and not stripped.startswith("%")
            and NON_MATHLIKE_RE.search(stripped)
        ):
            out_lines.extend(close_active())

        out_lines.append(line)

        code = split_comment(line)
        for m in token_re.finditer(code):
            token = m.group(0)
            begin_env = m.group(1)
            end_env = m.group(2)
            if begin_env:
                if mode is not None and begin_env in DISPLAY_SCOPED_ENVS:
                    display_env_stack.append(begin_env)
                continue
            if end_env:
                if mode is not None and display_env_stack and display_env_stack[-1] == end_env:
                    display_env_stack.pop()
                continue
            if token == r"\[":
                mode = "bracket"
                continue
            if token == r"\]":
                if mode == "bracket":
                    mode = None
                    display_env_stack.clear()
                continue
            if token == r"\(":
                if mode is None:
                    mode = "paren"
                continue
            if token == r"\)":
                if mode == "paren":
                    mode = None
                    display_env_stack.clear()
                continue
            if token == "$$":
                if mode == "dollar":
                    mode = None
                    display_env_stack.clear()
                elif mode is None:
                    mode = "dollar"
                else:
                    mode = "dollar"

    if mode is not None:
        out_lines.extend(close_active())

    out = "\n".join(out_lines).rstrip() + "\n"
    return out


def repair_environment_balance(text: str) -> str:
    """Repair begin/end environment balance by local stack correction."""
    out: List[str] = []
    stack: List[str] = []
    last = 0
    for m in BEGIN_END_RE.finditer(text):
        out.append(text[last : m.start()])
        kind = m.group("kind")
        env = m.group("env")
        token = m.group(0)
        if kind == "begin":
            stack.append(env)
            out.append(token)
        else:
            if stack and stack[-1] == env:
                stack.pop()
                out.append(token)
            elif env in stack:
                while stack and stack[-1] != env:
                    out.append(f"\\end{{{stack.pop()}}}")
                if stack and stack[-1] == env:
                    stack.pop()
                    out.append(token)
            else:
                # Drop orphan \end{...}.
                pass
        last = m.end()
    out.append(text[last:])
    while stack:
        out.append(f"\n\\end{{{stack.pop()}}}")
    return "".join(out)


def rewrite_text_macros_with_embedded_math(text: str) -> str:
    """Rewrite \\text{(...math...) CJK} into \\text{$(...math...)$ CJK}."""

    def degrade_tex_math_macros_to_plain_text(s: str) -> str:
        # Unwrap style/operator wrappers first so symbol mapping can see inner tokens.
        wrapper_pat = re.compile(
            r"\\(?:mathrm|mathsf|mathbf|mathit|mathcal|mathbb|operatorname)\s*\{([^{}]*)\}"
        )
        prev = None
        while s != prev:
            prev = s
            # Keep a boundary around unwrapped content so adjacent macros
            # (e.g., \in\mathrm{Sym}) do not merge into one command token.
            s = wrapper_pat.sub(r"{\1}", s)

        symbol_map = {
            "ell": "ell",
            "in": " in ",
            "notin": " notin ",
            "to": "->",
            "rightarrow": "->",
            "leftarrow": "<-",
            "cdot": "*",
            "times": "x",
            "le": "<=",
            "ge": ">=",
            "neq": "!=",
            "subset": " subset ",
            "subseteq": " subseteq ",
            "supset": " supset ",
            "supseteq": " supseteq ",
            "cup": " cup ",
            "cap": " cap ",
            "land": " and ",
            "lor": " or ",
            "forall": " forall ",
            "exists": " exists ",
            "sum": "sum",
            "prod": "prod",
            "int": "int",
            "partial": "partial",
            "nabla": "nabla",
            "alpha": "alpha",
            "beta": "beta",
            "gamma": "gamma",
            "delta": "delta",
            "epsilon": "epsilon",
            "zeta": "zeta",
            "eta": "eta",
            "theta": "theta",
            "lambda": "lambda",
            "mu": "mu",
            "nu": "nu",
            "pi": "pi",
            "rho": "rho",
            "sigma": "sigma",
            "tau": "tau",
            "phi": "phi",
            "chi": "chi",
            "psi": "psi",
            "omega": "omega",
            "Gamma": "Gamma",
            "Delta": "Delta",
            "Theta": "Theta",
            "Lambda": "Lambda",
            "Xi": "Xi",
            "Pi": "Pi",
            "Sigma": "Sigma",
            "Phi": "Phi",
            "Psi": "Psi",
            "Omega": "Omega",
        }
        drop_macros = {
            "left",
            "right",
            "big",
            "Big",
            "bigl",
            "bigr",
            "Bigl",
            "Bigr",
            "displaystyle",
            "textstyle",
            "scriptstyle",
            "scriptscriptstyle",
            "quad",
            "qquad",
        }

        def _macro_repl(m: re.Match[str]) -> str:
            cmd = m.group(1)
            if cmd in symbol_map:
                return symbol_map[cmd]
            if cmd in drop_macros:
                return ""
            return cmd

        s = re.sub(r"\\([A-Za-z@]+)", _macro_repl, s)
        # Keep escaped special chars as literal chars in degraded text.
        s = s.replace(r"\{", "{").replace(r"\}", "}").replace(r"\_", "_").replace(r"\^", "^")
        s = s.replace("{", "").replace("}", "")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def escape_unescaped_text_chars(s: str) -> str:
        buf: List[str] = []
        prev_backslash = False
        for ch in s:
            if ch in {"_", "^"} and not prev_backslash:
                buf.append("\\")
                buf.append(ch)
                prev_backslash = False
                continue
            buf.append(ch)
            prev_backslash = (ch == "\\")
        return "".join(buf)

    out: List[str] = []
    i = 0
    n = len(text)
    marker = r"\text{"

    while i < n:
        if not text.startswith(marker, i):
            out.append(text[i])
            i += 1
            continue

        start = i + len(marker)
        j = start
        depth = 1
        while j < n and depth > 0:
            ch = text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1

        if depth != 0:
            out.append(text[i:])
            break

        content = text[start : j - 1]
        replacement = None
        if "\\" in content and any(ord(c) > 127 for c in content):
            stripped = content.strip()
            if stripped.startswith("(") and ")" in stripped:
                close_idx = stripped.rfind(")")
                expr = stripped[: close_idx + 1].strip()
                tail = stripped[close_idx + 1 :].strip()
                if expr and tail and "\\" in expr:
                    replacement = r"\text{$" + expr + "$ " + tail + "}"

        if replacement is not None:
            out.append(replacement)
        else:
            safe_content = escape_unescaped_text_chars(content)
            if "\\" in safe_content and any(ord(c) > 127 for c in safe_content):
                # Fallback: degrade TeX math macros inside \text{...} to plain text.
                plain = degrade_tex_math_macros_to_plain_text(safe_content)
                safe_content = escape_unescaped_text_chars(plain)
            out.append(r"\text{" + safe_content + "}")
        i = j

    return "".join(out)


def normalize_invalid_star_macro(text: str) -> str:
    """Replace invalid TeX control symbol \\* with \\ast in fragments.

    Some extracted math snippets use forms like `\\sigma_\\*` for pushforward.
    `\\*` is not a valid control symbol in this context and breaks compile.
    """

    if r"\*" not in text:
        return text
    return text.replace(r"\*", r"\ast")


def normalize_hyperref_title_fragments(text: str) -> str:
    """Repair fragile hyperref title strings that contain raw #."""

    if "{#}" not in text and r"\texorpdfstring" not in text:
        return text
    text = text.replace(r"\texorpdfstring{\(\#\)}{#}", r"\texorpdfstring{\(\#\)}{\#}")
    text = text.replace("{#}", r"{\#}")
    return text


def extract_source_preamble(source_main_tex: Path) -> str:
    try:
        text = source_main_tex.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = BEGIN_DOCUMENT_RE.search(text)
    if not m:
        return ""
    return text[: m.start()].rstrip()


def normalize_atom_tex_for_packed_index(text: str) -> str:
    out: List[str] = []
    explicit_list_depth = 0
    auto_itemize_open = False
    list_item_started: List[bool] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            continue
        if LATEXPAND_ARTIFACT_LINE_RE.search(line):
            # Drop latexpand explain markers that leaked into fragment payload.
            continue
        if ENDINPUT_LINE_RE.match(stripped):
            # \endinput terminates file reading and would truncate packed index builds.
            continue
        if stripped == r"\phantomsection":
            continue
        if KGID_LABEL_LINE_RE.match(stripped):
            continue
        if auto_itemize_open and AUTO_ITEMIZE_CLOSE_HINT_RE.match(stripped):
            out.append(r"\end{itemize}")
            auto_itemize_open = False
        if LIST_ENV_BEGIN_RE.match(stripped):
            explicit_list_depth += 1
            list_item_started.append(False)
        if ITEM_LINE_RE.match(stripped) and explicit_list_depth == 0 and not auto_itemize_open:
            out.append(r"\begin{itemize}")
            auto_itemize_open = True
        if ITEM_LINE_RE.match(stripped) and list_item_started:
            list_item_started[-1] = True
        if (
            list_item_started
            and not list_item_started[-1]
            and stripped
            and not LIST_ENV_BEGIN_RE.match(stripped)
            and not LIST_ENV_END_RE.match(stripped)
        ):
            # List environments that start with raw text are invalid in LaTeX.
            # Promote the first content line to an explicit item.
            out.append(r"\item " + stripped)
            list_item_started[-1] = True
        else:
            out.append(line)
        if LIST_ENV_END_RE.match(stripped):
            explicit_list_depth = max(0, explicit_list_depth - 1)
            if list_item_started:
                list_item_started.pop()
    if auto_itemize_open:
        out.append(r"\end{itemize}")
    normalized = "\n".join(out).strip() + "\n"
    normalized = repair_environment_balance(normalized)
    normalized = repair_display_math_balance(normalized)
    normalized = close_display_before_non_math_text(normalized)
    normalized = repair_environment_balance(normalized)
    normalized = rewrite_text_macros_with_embedded_math(normalized)
    normalized = normalize_invalid_star_macro(normalized)
    normalized = normalize_hyperref_title_fragments(normalized)
    return normalized


def split_ref_labels_for_rewrite(raw: str) -> List[str]:
    out: List[str] = []
    for part in raw.split(","):
        token = part.strip()
        if token:
            out.append(token)
    return out


def normalize_label_alias_forms(label: str) -> Set[str]:
    value = label.strip()
    out = {value}
    if ":" in value:
        out.add(value.replace(":", "__"))
    if "__" in value:
        out.add(value.replace("__", ":"))
    return {x for x in out if x}


def load_reference_alias_map(kg_root: Path) -> Dict[str, str]:
    alias_path = kg_root / "schema" / "reference_aliases.json"
    if not alias_path.exists():
        return {}
    try:
        payload = json.loads(alias_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    out: Dict[str, str] = {}
    for raw_src, raw_dst in payload.items():
        src = str(raw_src or "").strip()
        dst = str(raw_dst or "").strip()
        if not src or not dst:
            continue
        for src_form in normalize_label_alias_forms(src):
            out[src_form] = dst
    return out


def rewrite_ref_aliases(text: str, alias_map: Dict[str, str]) -> str:
    if not alias_map:
        return text

    def repl(match: re.Match[str]) -> str:
        cmd = match.group("cmd")
        arg = match.group("arg")
        labels = split_ref_labels_for_rewrite(arg)
        if not labels:
            return match.group(0)
        rewritten = [alias_map.get(lb, lb) for lb in labels]
        return "\\" + cmd + "{" + ",".join(rewritten) + "}"

    return REF_MACRO_WITH_ARG_RE.sub(repl, text)


def build_packed_index_input(
    index_path: Path,
    build_dir: Path,
    *,
    alias_map: Dict[str, str] | None = None,
) -> Path:
    aliases = alias_map or {}
    lines = index_path.read_text(encoding="utf-8", errors="replace").splitlines()
    packed_lines: List[str] = []
    for line in lines:
        m = KGINPUT_LINE_RE.match(line)
        if not m:
            # Drop generated mapping comments to reduce TeX string-pool pressure.
            if line.lstrip().startswith("% KG-"):
                continue
            packed_lines.append(line)
            continue
        rel = m.group("rel")
        atom_link = (index_path.parent / rel)
        atom_path = atom_link.resolve(strict=True)
        atom_text = atom_path.read_text(encoding="utf-8", errors="replace")
        normalized = normalize_atom_tex_for_packed_index(atom_text)
        normalized = rewrite_ref_aliases(normalized, aliases)
        packed_lines.append(normalized.rstrip())
        packed_lines.append(r"\kgcloseproofifopen")
    packed_path = build_dir / f"{index_path.stem}.packed.tex"
    packed_path.write_text("\n".join(packed_lines).rstrip() + "\n", encoding="utf-8")
    return packed_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile KG views via latexmk.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--mode", choices=["audit", "index", "partial"], required=True)
    parser.add_argument("--root", help="Root label for audit mode")
    parser.add_argument("--label", help="Target label for partial mode")
    parser.add_argument("--spec", help="Index spec name/path for index mode")
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help="Index mode only: compile atoms affected by new source deltas since last marker.",
    )
    parser.add_argument(
        "--changed-bootstrap",
        choices=["mark-current", "include-all"],
        default="mark-current",
        help="When --changed-only has no marker yet: mark-current=initialize marker without compile, include-all=compile all known deltas.",
    )
    parser.add_argument(
        "--index-ref-mode",
        choices=["stable", "strict"],
        default="strict",
        help=(
            "Index mode reference behavior: strict=keep native refs/cites; "
            "stable=keep refs native when resolvable and only fallback on unresolved refs."
        ),
    )
    parser.add_argument(
        "--degrade-cite",
        action="store_true",
        help=(
            "Only used with --index-ref-mode stable: degrade \\cite-family commands "
            "to raw keys instead of running bibliography resolution."
        ),
    )
    parser.add_argument(
        "--latexmk-cmd",
        default="latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error",
        help="latexmk command prefix",
    )
    parser.add_argument(
        "--fresh-build",
        action="store_true",
        help="Use a timestamped build directory. Default reuses a stable target build dir for incremental speed.",
    )
    parser.add_argument(
        "--verbose-latex",
        action="store_true",
        help="Stream latexmk output. Default writes latex output to file for faster builds.",
    )
    parser.add_argument(
        "--single-pass",
        action="store_true",
        help="Run a single XeLaTeX pass instead of latexmk (faster, less reference convergence).",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Fail on first TeX error using single-pass XeLaTeX (debug mode).",
    )
    parser.add_argument(
        "--full-latexmk",
        action="store_true",
        help="Disable fail-fast default and use latexmk multi-pass mode.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only generate tex, do not run latexmk")
    return parser.parse_args()


def build_main_tex(
    inputs: Sequence[Path],
    *,
    fragment_ref_mode: bool = False,
    degrade_cite: bool = False,
    source_main_tex: Path | None = None,
    tail_lines: Sequence[str] = (),
    include_toc_frontmatter: bool = False,
) -> str:
    lines: List[str] = []
    lines.append("\\ifdefined\\pdfoutput\\pdfoutput=1\\fi")
    if source_main_tex is not None:
        source_preamble = extract_source_preamble(source_main_tex)
        if source_preamble:
            lines.append(source_preamble)
        else:
            lines.append("\\documentclass[11pt,letterpaper,fontset=fandol]{ctexart}")
            lines.append("\\usepackage{amsmath,amssymb,amsthm}")
            lines.append("\\usepackage{hyperref}")
            lines.append("\\usepackage{subfiles}")
        # When source preamble is used, avoid redeclaring theorem/macros.
        lines.append("\\providecommand{\\kgref}[1]{\\ref{kg:#1}}")
        # Safe fallback symbols for atom fragments that may not be in source preamble.
        lines.append("\\providecommand{\\RR}{\\mathbb{R}}")
        lines.append("\\providecommand{\\CC}{\\mathbb{C}}")
        lines.append("\\providecommand{\\QQ}{\\mathbb{Q}}")
        lines.append("\\providecommand{\\FF}{\\mathbb{F}}")
        lines.append("\\providecommand{\\ZZ}{\\mathbb{Z}}")
        lines.append("\\providecommand{\\NN}{\\mathbb{N}}")
        lines.append("\\providecommand{\\PP}{\\mathbb{P}}")
        lines.append("\\providecommand{\\TT}{\\mathbb{T}}")
        lines.append("\\providecommand{\\EE}{\\mathbb{E}}")
        lines.append("\\providecommand{\\E}{\\mathbb{E}}")
        lines.append("\\providecommand{\\Var}{\\operatorname{Var}}")
        lines.append("\\providecommand{\\Cov}{\\operatorname{Cov}}")
        lines.append("\\providecommand{\\Tr}{\\operatorname{Tr}}")
        lines.append("\\providecommand{\\Span}{\\operatorname{Span}}")
        lines.append("\\providecommand{\\Mat}{\\operatorname{Mat}}")
        lines.append("\\providecommand{\\Fold}{\\operatorname{Fold}}")
        lines.append("\\providecommand{\\tr}{\\operatorname{tr}}")
        lines.append("\\providecommand{\\Ind}{\\operatorname{Ind}}")
        lines.append("\\providecommand{\\Disc}{\\operatorname{Disc}}")
        lines.append("\\providecommand{\\End}{\\operatorname{End}}")
        lines.append("\\providecommand{\\Hom}{\\operatorname{Hom}}")
        lines.append("\\providecommand{\\Ext}{\\operatorname{Ext}}")
        lines.append("\\providecommand{\\Aut}{\\operatorname{Aut}}")
        lines.append("\\providecommand{\\Gal}{\\operatorname{Gal}}")
        lines.append("\\providecommand{\\Tor}{\\operatorname{Tor}}")
        lines.append("\\providecommand{\\Lie}{\\operatorname{Lie}}")
        lines.append("\\providecommand{\\GL}{\\operatorname{GL}}")
        lines.append("\\providecommand{\\rank}{\\operatorname{rank}}")
        lines.append("\\providecommand{\\Spec}{\\operatorname{Spec}}")
        lines.append("\\providecommand{\\Pic}{\\operatorname{Pic}}")
        lines.append("\\providecommand{\\Div}{\\operatorname{Div}}")
        lines.append("\\providecommand{\\ord}{\\operatorname{ord}}")
        lines.append("\\providecommand{\\Res}{\\operatorname{Res}}")
        lines.append("\\providecommand{\\Jac}{\\operatorname{Jac}}")
        lines.append("\\providecommand{\\Prym}{\\operatorname{Prym}}")
        lines.append("\\providecommand{\\Sym}{\\operatorname{Sym}}")
        lines.append("\\providecommand{\\Inn}{\\operatorname{Inn}}")
        lines.append("\\providecommand{\\Out}{\\operatorname{Out}}")
        lines.append("\\providecommand{\\ad}{\\operatorname{ad}}")
        lines.append("\\providecommand{\\Ad}{\\operatorname{Ad}}")
        lines.append("\\providecommand{\\Fix}{\\operatorname{Fix}}")
        lines.append("\\providecommand{\\Stab}{\\operatorname{Stab}}")
        lines.append("\\providecommand{\\Orb}{\\operatorname{Orb}}")
        lines.append("\\providecommand{\\Supp}{\\operatorname{Supp}}")
        lines.append("\\providecommand{\\id}{\\operatorname{id}}")
        lines.append("\\providecommand{\\Id}{\\operatorname{Id}}")
        lines.append("\\providecommand{\\diag}{\\operatorname{diag}}")
        lines.append("\\providecommand{\\sgn}{\\operatorname{sgn}}")
        lines.append("\\providecommand{\\cdim}{\\operatorname{cdim}}")
        lines.append("\\providecommand{\\pcdim}{\\operatorname{pcdim}}")
        lines.append("\\providecommand{\\Den}{\\operatorname{Den}}")
        lines.append("\\providecommand{\\Log}{\\log}")
        lines.append("\\providecommand{\\Mult}{\\operatorname{Mult}}")
        lines.append("\\providecommand{\\poly}{\\operatorname{poly}}")
        lines.append("\\providecommand{\\ket}[1]{\\left\\lvert #1\\right\\rangle}")
        lines.append("\\providecommand{\\bra}[1]{\\left\\langle #1\\right\\rvert}")
        lines.append("\\providecommand{\\braket}[1]{\\left\\langle #1\\right\\rangle}")
        lines.append("\\providecommand{\\ketbra}[2]{\\left\\lvert #1\\right\\rangle\\left\\langle #2\\right\\rvert}")
        lines.append("\\providecommand{\\abs}[1]{\\left\\lvert #1\\right\\rvert}")
        lines.append("\\providecommand{\\norm}[1]{\\left\\lVert #1\\right\\rVert}")
    else:
        lines.append("\\documentclass[11pt,letterpaper,fontset=fandol]{ctexart}")
        lines.append("% Silence spurious missing-char noise in large merged builds.")
        lines.append("\\tracinglostchars=0\\relax")
        lines.append("\\usepackage{geometry}")
        lines.append("\\geometry{letterpaper, margin=1in}")
        lines.append("\\usepackage{amsmath,amssymb,amsthm}")
        lines.append("\\usepackage{mathtools}")
        lines.append("\\usepackage{amscd}")
        lines.append("\\makeatletter")
        lines.append("\\@ifundefined{FASTBUILD}{%")
        lines.append("  \\usepackage{graphicx}%")
        lines.append("}{%")
        lines.append("  \\usepackage[draft]{graphicx}%")
        lines.append("}%")
        lines.append("\\makeatother")
        lines.append("\\makeatletter")
        lines.append("\\let\\origincludegraphics\\includegraphics")
        lines.append("\\renewcommand{\\includegraphics}[2][]{%")
        lines.append("  \\IfFileExists{#2}{%")
        lines.append("    \\origincludegraphics[#1]{#2}%")
        lines.append("  }{%")
        lines.append("    \\fbox{\\ttfamily missing graphic: \\detokenize{#2}}%")
        lines.append("  }%")
        lines.append("}%")
        lines.append("\\makeatother")
        lines.append("\\usepackage{hyperref}")
        lines.append("\\usepackage{subfiles}")
        lines.append("\\usepackage{cite}")
        lines.append("\\usepackage{xcolor}")
        lines.append("\\usepackage{float}")
        lines.append("\\usepackage{placeins}")
        lines.append("\\usepackage{booktabs}")
        lines.append("\\usepackage{array}")
        lines.append("\\usepackage{adjustbox}")
        lines.append("\\usepackage{etoolbox}")
        lines.append("\\usepackage{fvextra}")
        lines.append("\\usepackage{verbatim}")
        lines.append("\\usepackage{url}")
        lines.append("\\usepackage[strings]{underscore}")
        lines.append("\\usepackage{mathrsfs}")
        lines.append("\\usepackage{dsfont}")
        lines.append("\\newtheorem{theorem}{Theorem}[section]")
        lines.append("\\newtheorem{lemma}[theorem]{Lemma}")
        lines.append("\\newtheorem{definition}[theorem]{Definition}")
        lines.append("\\newtheorem{proposition}[theorem]{Proposition}")
        lines.append("\\newtheorem{corollary}[theorem]{Corollary}")
        lines.append("\\newtheorem{conjecture}[theorem]{Conjecture}")
        lines.append("\\newtheorem{conclusion}[theorem]{Conclusion}")
        lines.append("\\newtheorem{example}[theorem]{Example}")
        lines.append("\\newtheorem{algorithm}[theorem]{Algorithm}")
        lines.append("\\newtheorem{auditthm}{Theorem}")
        lines.append("\\newtheorem{auditcor}[auditthm]{Corollary}")
        lines.append("\\newtheorem{auditprop}[auditthm]{Proposition}")
        lines.append("\\newtheorem{remark}[theorem]{Remark}")
        lines.append("\\DeclareMathOperator{\\tr}{tr}")
        lines.append("\\DeclareMathOperator{\\Ind}{Ind}")
        lines.append("\\DeclareMathOperator{\\Disc}{Disc}")
        lines.append("\\newcommand{\\RR}{\\mathbb{R}}")
        lines.append("\\newcommand{\\CC}{\\mathbb{C}}")
        lines.append("\\newcommand{\\QQ}{\\mathbb{Q}}")
        lines.append("\\newcommand{\\FF}{\\mathbb{F}}")
        lines.append("\\newcommand{\\ZZ}{\\mathbb{Z}}")
        lines.append("\\newcommand{\\NN}{\\mathbb{N}}")
        lines.append("\\newcommand{\\PP}{\\mathbb{P}}")
        lines.append("\\newcommand{\\TT}{\\mathbb{T}}")
        lines.append("\\newcommand{\\EE}{\\mathbb{E}}")
        lines.append("\\providecommand{\\E}{\\mathbb{E}}")
        lines.append("\\newcommand{\\Var}{\\mathrm{Var}}")
        lines.append("\\newcommand{\\Cov}{\\operatorname{Cov}}")
        lines.append("\\newcommand{\\Sol}{\\Sigma_{\\mathrm{sol}}}")
        lines.append("\\newcommand{\\dd}{\\mathrm{d}}")
        lines.append("\\newcommand{\\ind}{\\mathbf{1}}")
        lines.append("\\newcommand{\\card}[1]{\\left\\lvert #1\\right\\rvert}")
        lines.append("\\newcommand{\\Tr}{\\mathrm{Tr}}")
        lines.append("\\newcommand{\\Span}{\\mathrm{Span}}")
        lines.append("\\newcommand{\\Mat}{\\mathrm{Mat}}")
        lines.append("\\newcommand{\\Fold}{\\mathrm{Fold}}")
        lines.append("\\providecommand{\\End}{\\operatorname{End}}")
        lines.append("\\providecommand{\\Hom}{\\operatorname{Hom}}")
        lines.append("\\providecommand{\\Ext}{\\operatorname{Ext}}")
        lines.append("\\providecommand{\\Aut}{\\operatorname{Aut}}")
        lines.append("\\providecommand{\\Gal}{\\operatorname{Gal}}")
        lines.append("\\providecommand{\\Tor}{\\operatorname{Tor}}")
        lines.append("\\providecommand{\\Lie}{\\operatorname{Lie}}")
        lines.append("\\providecommand{\\GL}{\\operatorname{GL}}")
        lines.append("\\providecommand{\\rank}{\\operatorname{rank}}")
        lines.append("\\providecommand{\\Spec}{\\operatorname{Spec}}")
        lines.append("\\providecommand{\\Pic}{\\operatorname{Pic}}")
        lines.append("\\providecommand{\\Div}{\\operatorname{Div}}")
        lines.append("\\providecommand{\\ord}{\\operatorname{ord}}")
        lines.append("\\providecommand{\\Res}{\\operatorname{Res}}")
        lines.append("\\providecommand{\\Jac}{\\operatorname{Jac}}")
        lines.append("\\providecommand{\\Prym}{\\operatorname{Prym}}")
        lines.append("\\providecommand{\\Sym}{\\operatorname{Sym}}")
        lines.append("\\providecommand{\\Inn}{\\operatorname{Inn}}")
        lines.append("\\providecommand{\\Out}{\\operatorname{Out}}")
        lines.append("\\providecommand{\\ad}{\\operatorname{ad}}")
        lines.append("\\providecommand{\\Ad}{\\operatorname{Ad}}")
        lines.append("\\providecommand{\\Fix}{\\operatorname{Fix}}")
        lines.append("\\providecommand{\\Stab}{\\operatorname{Stab}}")
        lines.append("\\providecommand{\\Orb}{\\operatorname{Orb}}")
        lines.append("\\providecommand{\\Supp}{\\operatorname{Supp}}")
        lines.append("\\providecommand{\\id}{\\operatorname{id}}")
        lines.append("\\providecommand{\\Id}{\\operatorname{Id}}")
        lines.append("\\providecommand{\\diag}{\\operatorname{diag}}")
        lines.append("\\providecommand{\\sgn}{\\operatorname{sgn}}")
        lines.append("\\providecommand{\\cdim}{\\operatorname{cdim}}")
        lines.append("\\providecommand{\\pcdim}{\\operatorname{pcdim}}")
        lines.append("\\providecommand{\\Den}{\\operatorname{Den}}")
        lines.append("\\providecommand{\\dashmapsto}{\\mapsto}")
        lines.append("\\providecommand{\\longtwoheadrightarrow}{\\relbar\\joinrel\\twoheadrightarrow}")
        lines.append("\\providecommand{\\Log}{\\log}")
        lines.append("\\providecommand{\\Mult}{\\operatorname{Mult}}")
        lines.append("\\providecommand{\\poly}{\\operatorname{poly}}")
        lines.append("\\providecommand{\\ket}[1]{\\left\\lvert #1\\right\\rangle}")
        lines.append("\\providecommand{\\bra}[1]{\\left\\langle #1\\right\\rvert}")
        lines.append("\\providecommand{\\braket}[1]{\\left\\langle #1\\right\\rangle}")
        lines.append("\\providecommand{\\ketbra}[2]{\\left\\lvert #1\\right\\rangle\\left\\langle #2\\right\\rvert}")
        lines.append("\\newcommand{\\abs}[1]{\\left\\lvert #1\\right\\rvert}")
        lines.append("\\newcommand{\\norm}[1]{\\left\\lVert #1\\right\\rVert}")
        lines.append("\\newcommand{\\kgref}[1]{\\ref{kg:#1}}")
    lines.append("\\makeatletter")
    lines.append("\\@ifundefined{c@genfrag}{\\newcounter{genfrag}[section]}{}")
    lines.append("\\makeatother")
    lines.append("\\renewcommand{\\thegenfrag}{\\thesection.\\arabic{genfrag}}")
    lines.append("\\providecommand{\\genfraglabel}[1]{\\refstepcounter{genfrag}\\label{#1}}")
    if fragment_ref_mode:
        lines.append("\\makeatletter")
        lines.append("\\newcommand{\\kgrawref}[1]{\\texttt{#1}}")
        lines.append("\\hbadness=10000")
        lines.append("\\hfuzz=1000pt")
        if degrade_cite:
            lines.append("\\renewcommand{\\cite}[1]{\\kgrawref{#1}}")
            lines.append("\\@ifundefined{citep}{\\providecommand{\\citep}[1]{\\kgrawref{#1}}}{}")
            lines.append("\\@ifundefined{citet}{\\providecommand{\\citet}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\@ifundefined{autoref}{\\providecommand{\\autoref}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\@ifundefined{cref}{\\providecommand{\\cref}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\@ifundefined{Cref}{\\providecommand{\\Cref}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\@ifundefined{pageref}{\\providecommand{\\pageref}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\@ifundefined{nameref}{\\providecommand{\\nameref}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\@ifundefined{vref}{\\providecommand{\\vref}[1]{\\kgrawref{#1}}}{}")
        lines.append("\\def\\@setref#1#2#3{\\ifx#1\\relax\\kgrawref{#3}\\else\\expandafter#2#1\\@empty\\@empty\\@empty\\null\\fi}")
        lines.append("\\makeatother")
    lines.append("\\makeatletter")
    lines.append("\\newcommand{\\kgcloseproofifopen}{%")
    lines.append("  \\edef\\kgcurrenv{\\@currenvir}%")
    lines.append("  \\def\\kgproofenv{proof}%")
    lines.append("  \\ifx\\kgcurrenv\\kgproofenv\\end{proof}\\fi%")
    lines.append("}")
    lines.append("\\newcommand{\\kginput}[1]{\\input{#1}\\kgcloseproofifopen}")
    lines.append("\\makeatother")
    lines.append("\\begin{document}")
    lines.append("\\sloppy")
    lines.append("\\hfuzz=\\maxdimen\\relax")
    if include_toc_frontmatter:
        lines.append("\\begingroup")
        lines.append("\\tracinglostchars=0\\relax")
        lines.append("\\makeatletter")
        lines.append("\\let\\input@path\\@empty")
        lines.append("\\makeatother")
        lines.append("\\tableofcontents")
        lines.append("\\endgroup")
        lines.append("\\newpage")
    if source_main_tex is not None:
        # Keep entrypoint framing close to source book output quality.
        lines.append("\\maketitle")
        lines.append("\\begingroup")
        lines.append("\\tracinglostchars=0\\relax")
        lines.append("\\makeatletter")
        lines.append("\\let\\input@path\\@empty")
        lines.append("\\makeatother")
        lines.append("\\tableofcontents")
        lines.append("\\endgroup")
        lines.append("\\newpage")
    for p in inputs:
        lines.append(f"\\input{{{p.as_posix()}}}")
    for line in tail_lines:
        clean = line.strip()
        if clean:
            lines.append(clean)
    lines.append("\\end{document}")
    return "\n".join(lines) + "\n"


def compile_with_latexmk(
    build_dir: Path,
    main_tex: Path,
    latexmk_cmd: str,
    kg_root: Path,
    inputs: Sequence[Path],
    extra_texinputs: Sequence[Path] = (),
    verbose_latex: bool = False,
) -> tuple[int, Path]:
    env = build_texinputs_env(kg_root, inputs, extra_texinputs)
    # Force the local build entrypoint; avoid TEXINPUTS "main.tex" shadowing.
    cmd = shlex.split(latexmk_cmd) + [f"./{main_tex.name}"]
    latex_log_path = build_dir / "latexmk.stdout.log"
    if verbose_latex:
        proc = subprocess.run(cmd, cwd=build_dir, env=env)
    else:
        with latex_log_path.open("w", encoding="utf-8") as fh:
            proc = subprocess.run(
                cmd,
                cwd=build_dir,
                env=env,
                stdout=fh,
                stderr=subprocess.STDOUT,
                text=True,
            )
    return proc.returncode, latex_log_path


def build_texinputs_env(
    kg_root: Path,
    inputs: Sequence[Path],
    extra_texinputs: Sequence[Path] = (),
) -> dict:
    env = os.environ.copy()
    texinputs = env.get("TEXINPUTS", "")
    search_dirs: List[str] = []

    def add_dir(path: Path) -> None:
        p = path.resolve().as_posix()
        if p not in search_dirs:
            search_dirs.append(p)

    add_dir(kg_root)
    add_dir(kg_root / "atoms")
    for p in inputs:
        add_dir(p.parent)
        atoms_alias = p.parent / "atoms"
        if atoms_alias.exists():
            add_dir(atoms_alias)
    for p in extra_texinputs:
        add_dir(p)

    prefix = ":".join(search_dirs)
    env["TEXINPUTS"] = f"{prefix}:{texinputs}" if texinputs else f"{prefix}:"
    return env


def compile_single_pass_xelatex(
    build_dir: Path,
    main_tex: Path,
    kg_root: Path,
    inputs: Sequence[Path],
    extra_texinputs: Sequence[Path] = (),
    verbose_latex: bool = False,
) -> tuple[int, Path]:
    env = build_texinputs_env(kg_root, inputs, extra_texinputs)
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"./{main_tex.name}",
    ]
    latex_log_path = build_dir / "xelatex.stdout.log"
    if verbose_latex:
        proc = subprocess.run(cmd, cwd=build_dir, env=env)
    else:
        with latex_log_path.open("w", encoding="utf-8") as fh:
            proc = subprocess.run(
                cmd,
                cwd=build_dir,
                env=env,
                stdout=fh,
                stderr=subprocess.STDOUT,
                text=True,
            )
    return proc.returncode, latex_log_path


def tail_lines(path: Path, max_lines: int = 120) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def collect_tex_atoms_for_label(kg_root: Path, target_label: str) -> tuple[List[Path], List[tuple[Path, str]]]:
    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        raise RuntimeError("scan errors:\n" + "\n".join(scan_errors))

    by_label = {a.label: a for a in atoms}
    if target_label not in by_label:
        raise RuntimeError(f"label not found: {target_label}")

    selected: Set[str] = ancestor_closure([target_label], by_label)
    ordered = topological_order(atoms, subset=selected)
    tex_paths = [a.path.resolve() for a in ordered if a.ext == "tex"]
    includable: List[Path] = []
    skipped: List[tuple[Path, str]] = []
    for path in tex_paths:
        ok, reason = tex_input_fragment_status(path)
        if ok:
            includable.append(path)
        else:
            skipped.append((path, reason or "not input-fragment safe"))
    return includable, skipped


def resolve_index_entry(kg_root: Path, spec: str) -> Path:
    if not spec:
        raise RuntimeError("--spec is required for index mode")

    cmd = [
        "python3",
        str((kg_root / "scripts" / "kg_build_index.py").resolve()),
        "--kg-root",
        str(kg_root),
        "--spec",
        spec,
        "--print-path",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "kg_build_index.py failed")
    paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not paths:
        raise RuntimeError("kg_build_index.py did not return index path")
    return Path(paths[-1]).resolve()


def parse_index_labels(index_path: Path) -> Set[str]:
    labels: Set[str] = set()
    if not index_path.exists():
        return labels
    for line in index_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("% KG-"):
            continue
        parts = line[2:].strip().split()
        if len(parts) >= 3 and parts[0].startswith("KG-"):
            labels.add(parts[1])
    return labels


def discover_tex_project_root(source_path: Path) -> Path | None:
    cur = source_path.parent.resolve()
    while True:
        if (cur / "main.tex").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def discover_source_main_tex(extra_texinputs: Sequence[Path]) -> Path | None:
    candidates: List[Path] = []
    for path in extra_texinputs:
        main_tex = path / "main.tex"
        if main_tex.exists():
            candidates.append(main_tex.resolve())
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: len(p.as_posix()))[0]


def discover_merged_tex_from_emit_state(kg_root: Path) -> Path | None:
    state_path = kg_root / ".kgcache" / "merged" / "emit_state.json"
    if state_path.exists():
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        merged_tex_path = str(payload.get("merged_tex_path") or "").strip()
        if merged_tex_path:
            candidate = Path(merged_tex_path).expanduser()
            if not candidate.is_absolute():
                candidate = (kg_root / candidate).resolve()
            else:
                candidate = candidate.resolve()
            if candidate.exists():
                return candidate
    merged_dir = kg_root / ".kgcache" / "merged"
    candidates = sorted(
        merged_dir.glob("*.latexpanded.tex"),
        key=lambda p: (p.stat().st_mtime_ns, p.name),
    ) if merged_dir.exists() else []
    return candidates[-1].resolve() if candidates else None


def split_bibliography_items(arg: str) -> List[str]:
    items: List[str] = []
    cur: List[str] = []
    depth = 0
    for ch in arg:
        if ch == "{":
            depth += 1
            cur.append(ch)
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            cur.append(ch)
            continue
        if ch == "," and depth == 0:
            item = "".join(cur).strip()
            if item:
                items.append(item)
            cur = []
            continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail:
        items.append(tail)
    return items


def normalize_bibliography_item(item: str, source_root: Path | None) -> str:
    m = BIB_SUBFIX_ITEM_RE.fullmatch(item.strip())
    raw = m.group(1).strip() if m else item.strip()
    if not raw:
        return ""

    candidate = Path(raw)
    if source_root is not None:
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (source_root / raw).resolve()
        # BibTeX accepts paths without .bib suffix in \bibliography.
        if resolved.suffix.lower() == ".bib":
            resolved = resolved.with_suffix("")
        return resolved.as_posix()

    # Fallback: only strip \subfix wrapper and .bib suffix.
    if raw.endswith(".bib"):
        raw = raw[: -len(".bib")]
    return raw


def extract_bibliography_tail_lines(
    merged_tex_path: Path | None,
    source_main_tex: Path | None,
) -> List[str]:
    if merged_tex_path is None or not merged_tex_path.exists():
        return []
    try:
        text = merged_tex_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    style_line = ""
    bibliography_arg = ""
    for line in text.splitlines():
        if BIB_STYLE_LINE_RE.match(line):
            style_line = line.strip()
            continue
        if BIB_COMMAND_LINE_RE.match(line):
            bibliography_arg = line.strip()

    if not style_line and not bibliography_arg:
        return []

    out: List[str] = []
    if style_line:
        out.append(style_line)
    if bibliography_arg:
        m = re.match(r"^\s*\\bibliography\{(?P<arg>.*)\}\s*$", bibliography_arg)
        if m:
            arg = m.group("arg")
            source_root = source_main_tex.parent if source_main_tex is not None else None
            items = split_bibliography_items(arg)
            normalized = [
                normalize_bibliography_item(item, source_root)
                for item in items
            ]
            normalized = [x for x in normalized if x]
            if normalized:
                out.append(r"\bibliography{" + ",".join(normalized) + "}")
            else:
                out.append(bibliography_arg)
        else:
            out.append(bibliography_arg)
    return out


def extract_dag_bibliography_tail_lines(kg_root: Path) -> List[str]:
    bib_dir = kg_root / "bibliography"
    if not bib_dir.exists():
        return []
    bib_files = sorted(p for p in bib_dir.glob("*.bib") if p.is_file())
    if not bib_files:
        return []
    bib_roots = [p.resolve().with_suffix("").as_posix() for p in bib_files]
    return [
        r"\bibliographystyle{amsplain}",
        r"\bibliography{" + ",".join(bib_roots) + "}",
    ]


def build_missing_ref_anchor_lines(index_path: Path) -> List[str]:
    report_path = index_path.parent / "reference_closure_report.json"
    if not report_path.exists():
        return []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    missing = report.get("final_missing_refs")
    if not isinstance(missing, list):
        return []
    labels: List[str] = []
    seen: Set[str] = set()
    for raw in missing:
        label = str(raw or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    if not labels:
        return []
    lines: List[str] = []
    lines.append("% synthetic anchors for unresolved refs in index closure")
    for label in labels:
        escaped = label.replace("\\", "")
        lines.append(r"\ifdefined\genfraglabel\genfraglabel{" + escaped + r"}\else\phantomsection\label{" + escaped + r"}\fi")
    return lines


def collect_extra_texinputs_for_labels(kg_root: Path, labels: Set[str]) -> List[Path]:
    if not labels:
        return []
    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        raise RuntimeError("scan errors:\n" + "\n".join(scan_errors))
    by_label = {a.label: a for a in atoms}

    out: Set[Path] = set()
    for label in labels:
        atom = by_label.get(label)
        if atom is None:
            continue
        meta_path = atom_sidecar_path(atom.path)
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        source_path_raw = str(meta.get("source_path") or "").strip()
        if not source_path_raw:
            continue
        source_path = Path(source_path_raw).expanduser()
        if not source_path.is_absolute():
            source_path = (kg_root / source_path).resolve()
        else:
            source_path = source_path.resolve()
        if source_path.suffix.lower() != ".tex":
            continue

        out.add(source_path.parent)
        project_root = discover_tex_project_root(source_path)
        if project_root is not None:
            out.add(project_root)

    return sorted(out)


DELTA_FILE_RE = re.compile(r"^delta_(?P<ts>\d{8}T\d{6}Z)\.jsonl$")


def discover_source_deltas(kg_root: Path) -> List[tuple[str, Path]]:
    source_root = kg_root / ".kgcache" / "source"
    out: List[tuple[str, Path]] = []
    if not source_root.exists():
        return out
    for source_dir in sorted(source_root.iterdir()):
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.glob("delta_*.jsonl")):
            m = DELTA_FILE_RE.match(path.name)
            if not m:
                continue
            out.append((m.group("ts"), path.resolve()))
    out.sort(key=lambda x: x[0])
    return out


def compile_state_path(kg_root: Path, spec_name: str) -> Path:
    return kg_root / ".kgcache" / "compile_state" / f"index_{spec_name}_last_delta.txt"


def load_last_delta_ts(state_path: Path) -> str | None:
    if not state_path.exists():
        return None
    text = state_path.read_text(encoding="utf-8", errors="replace").strip()
    return text or None


def save_last_delta_ts(state_path: Path, ts: str) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(ts + "\n", encoding="utf-8")


def select_changed_deltas(
    deltas: Sequence[tuple[str, Path]], last_ts: str | None, bootstrap_mode: str
) -> tuple[List[Path], str | None]:
    if not deltas:
        return [], None
    newest_ts = deltas[-1][0]
    if last_ts:
        return [p for ts, p in deltas if ts > last_ts], newest_ts
    if bootstrap_mode == "include-all":
        return [p for _, p in deltas], newest_ts
    return [], newest_ts


def normalize_abs_path(raw: str) -> str:
    return str(Path(raw).expanduser().resolve())


def collect_changed_source_paths(delta_paths: Sequence[Path]) -> Set[str]:
    changed: Set[str] = set()
    for delta_path in delta_paths:
        for line in delta_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            change_type = str(rec.get("change_type") or "")
            if change_type in {"added", "modified", "deleted"}:
                p = rec.get("path")
                if p:
                    changed.add(normalize_abs_path(str(p)))
            elif change_type == "renamed":
                for key in ("old_path", "new_path"):
                    p = rec.get(key)
                    if p:
                        changed.add(normalize_abs_path(str(p)))
    return changed


def collect_changed_labels_from_meta(kg_root: Path, changed_source_paths: Set[str]) -> Set[str]:
    labels: Set[str] = set()
    atoms_dir = kg_root / "atoms"
    if not atoms_dir.exists() or not changed_source_paths:
        return labels
    for meta_path in atoms_dir.glob("*.meta.json"):
        try:
            rec = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        label = str(rec.get("label") or "").strip()
        source_path = str(rec.get("source_path") or "").strip()
        if not label or not source_path:
            continue
        if normalize_abs_path(source_path) in changed_source_paths:
            labels.add(label)
    return labels


def main() -> int:
    args = parse_args()
    if args.full_latexmk:
        args.single_pass = False
    elif args.fail_fast:
        args.single_pass = True
    elif not args.single_pass:
        # Default mode: fail-fast single-pass compile.
        args.single_pass = True
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

    pending_marker_state: Path | None = None
    pending_marker_ts: str | None = None
    extra_texinputs: List[Path] = []
    print("DAG-only compile: source preamble/texinputs/bibliography are disabled.")

    index_entry_path: Path | None = None
    if args.mode == "audit":
        if not args.root:
            raise SystemExit("--root is required for --mode audit")
        inputs, skipped = collect_tex_atoms_for_label(kg_root, args.root)
        target_name = f"audit_{args.root}"
    elif args.mode == "partial":
        if not args.label:
            raise SystemExit("--label is required for --mode partial")
        inputs, skipped = collect_tex_atoms_for_label(kg_root, args.label)
        target_name = f"partial_{args.label}"
    else:
        index_path = resolve_index_entry(kg_root, args.spec)
        index_entry_path = index_path
        spec_name = Path(args.spec).stem if args.spec else "index"
        index_labels = parse_index_labels(index_path)
        if args.changed_only:
            deltas = discover_source_deltas(kg_root)
            state_path = compile_state_path(kg_root, spec_name)
            last_ts = load_last_delta_ts(state_path)
            selected_delta_paths, newest_ts = select_changed_deltas(
                deltas, last_ts, args.changed_bootstrap
            )

            if not selected_delta_paths:
                if last_ts is None and newest_ts and args.changed_bootstrap == "mark-current":
                    save_last_delta_ts(state_path, newest_ts)
                    print(
                        f"Initialized changed-only marker for {spec_name} at {newest_ts}: {state_path}"
                    )
                else:
                    print(f"No new deltas for changed-only compile (spec={spec_name}).")
                return 0

            changed_paths = collect_changed_source_paths(selected_delta_paths)
            changed_labels = collect_changed_labels_from_meta(kg_root, changed_paths)
            if not changed_labels:
                if newest_ts:
                    save_last_delta_ts(state_path, newest_ts)
                print(f"No atoms matched changed source paths (spec={spec_name}).")
                return 0

            atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
            if scan_errors:
                raise RuntimeError("scan errors:\n" + "\n".join(scan_errors))
            by_label = {a.label: a for a in atoms}
            seed_labels = sorted(changed_labels & index_labels)
            if not seed_labels:
                if newest_ts:
                    save_last_delta_ts(state_path, newest_ts)
                print(f"Changed sources do not affect index spec {spec_name}.")
                return 0

            selected_labels = ancestor_closure(seed_labels, by_label) & index_labels
            ordered = topological_order(atoms, subset=selected_labels)
            inputs = []
            skipped = []
            for atom in ordered:
                if atom.ext != "tex":
                    continue
                ok, reason = tex_input_fragment_status(atom.path)
                if ok:
                    inputs.append(atom.path.resolve())
                else:
                    skipped.append((atom.path.resolve(), reason or "not input-fragment safe"))

            pending_marker_state = state_path
            pending_marker_ts = newest_ts
            target_name = f"index_{spec_name}_changed"
            print(
                f"Changed-only selection: deltas={len(selected_delta_paths)} "
                f"changed_labels={len(changed_labels)} seeds={len(seed_labels)} "
                f"selected_tex_inputs={len(inputs)}"
            )
        else:
            inputs = [index_path]
            skipped = []
            target_name = f"index_{spec_name}"

    for skipped_path, reason in skipped:
        print(f"Skipped non-fragment TeX atom: {skipped_path} ({reason})")

    if not inputs:
        raise SystemExit("No TeX inputs selected for compile")

    if args.fresh_build:
        build_dir = kg_root / ".kgcache" / "build" / f"{target_name}_{now_utc_compact()}"
    else:
        build_dir = kg_root / ".kgcache" / "build" / target_name
    build_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "index" and not args.changed_only:
        if len(inputs) != 1:
            raise RuntimeError(
                f"index mode expects exactly one index input, got {len(inputs)}"
            )
        packed_index = build_packed_index_input(
            inputs[0],
            build_dir,
            alias_map=load_reference_alias_map(kg_root),
        )
        print(f"Packed index input: {packed_index}")
        inputs = [packed_index]

    # Use absolute paths in generated main.tex to avoid relative path ambiguity.
    resolved_inputs = [Path(str(p)) for p in inputs]
    source_main_tex: Path | None = None
    post_body_lines: List[str] = []
    if args.mode == "index" and args.index_ref_mode == "strict":
        if index_entry_path is not None:
            anchor_lines = build_missing_ref_anchor_lines(index_entry_path)
            if anchor_lines:
                post_body_lines.extend(anchor_lines)
                print(f"Injecting synthetic ref anchors: {len(anchor_lines) - 1}")
        dag_bib_tail = extract_dag_bibliography_tail_lines(kg_root)
        if dag_bib_tail:
            post_body_lines.extend(dag_bib_tail)
            print(f"Using DAG bibliography files: {len(dag_bib_tail) - 1} command block")

    main_tex = build_dir / "main.tex"
    use_fragment_ref_mode = args.mode == "index" and args.index_ref_mode == "stable"
    main_tex.write_text(
        build_main_tex(
            resolved_inputs,
            fragment_ref_mode=use_fragment_ref_mode,
            degrade_cite=args.degrade_cite,
            source_main_tex=source_main_tex,
            tail_lines=post_body_lines,
            include_toc_frontmatter=(args.mode == "index"),
        ),
        encoding="utf-8",
    )
    print(f"Generated {main_tex}")

    if args.dry_run:
        return 0

    if args.single_pass:
        rc, latex_log_path = compile_single_pass_xelatex(
            build_dir,
            main_tex,
            kg_root,
            resolved_inputs,
            extra_texinputs=extra_texinputs,
            verbose_latex=args.verbose_latex,
        )
    else:
        rc, latex_log_path = compile_with_latexmk(
            build_dir,
            main_tex,
            args.latexmk_cmd,
            kg_root,
            resolved_inputs,
            extra_texinputs=extra_texinputs,
            verbose_latex=args.verbose_latex,
        )
    if rc != 0:
        mode_name = "xelatex(single-pass)" if args.single_pass else "latexmk"
        print(f"{mode_name} failed with code {rc}")
        if not args.verbose_latex:
            print(f"{mode_name} log: {latex_log_path}")
            tail = tail_lines(latex_log_path)
            if tail:
                print("---- compile tail ----")
                print(tail)
        return rc

    if pending_marker_state and pending_marker_ts:
        save_last_delta_ts(pending_marker_state, pending_marker_ts)
        print(f"Updated changed-only marker: {pending_marker_state} -> {pending_marker_ts}")

    if not args.verbose_latex:
        mode_name = "xelatex(single-pass)" if args.single_pass else "latexmk"
        print(f"{mode_name} log: {latex_log_path}")
    pdf_path = build_dir / "main.pdf"
    if pdf_path.exists():
        print(f"PDF: {pdf_path}")
    print(f"Compile succeeded: {build_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
