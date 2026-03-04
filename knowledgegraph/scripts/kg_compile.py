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
from typing import List, Sequence, Set

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
KGINPUT_LINE_RE = re.compile(r"^\s*\\kginput\{(?P<rel>atoms/KG-[^}]+\.tex)\}\s*$")
KGID_LABEL_LINE_RE = re.compile(r"^\s*\\label\{kgid:[^}]+\}\s*$")
LIST_ENV_BEGIN_RE = re.compile(r"^\s*\\begin\{(?:itemize|enumerate|description)\}")
LIST_ENV_END_RE = re.compile(r"^\s*\\end\{(?:itemize|enumerate|description)\}")
ITEM_LINE_RE = re.compile(r"^\s*\\item(?:\s|$|\[)")
AUTO_ITEMIZE_CLOSE_HINT_RE = re.compile(
    r"^\s*\\(?:kgcloseproofifopen|part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\b|"
    r"^\s*\\begin\{(?:theorem|lemma|proposition|corollary|definition|remark|example|proof|conjecture|conclusion|algorithm|auditthm|auditcor|auditprop|auditlem)\}"
)


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
    return "\n".join(out).strip() + "\n"


def build_packed_index_input(index_path: Path, build_dir: Path) -> Path:
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
        packed_lines.append(normalize_atom_tex_for_packed_index(atom_text).rstrip())
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
        lines.append("\\providecommand{\\diag}{\\operatorname{diag}}")
        lines.append("\\providecommand{\\sgn}{\\operatorname{sgn}}")
        lines.append("\\providecommand{\\cdim}{\\operatorname{cdim}}")
        lines.append("\\providecommand{\\pcdim}{\\operatorname{pcdim}}")
        lines.append("\\providecommand{\\Den}{\\operatorname{Den}}")
        lines.append("\\providecommand{\\Log}{\\log}")
        lines.append("\\providecommand{\\Mult}{\\operatorname{Mult}}")
        lines.append("\\providecommand{\\ket}[1]{\\left\\lvert #1\\right\\rangle}")
        lines.append("\\providecommand{\\bra}[1]{\\left\\langle #1\\right\\rvert}")
        lines.append("\\providecommand{\\braket}[1]{\\left\\langle #1\\right\\rangle}")
        lines.append("\\providecommand{\\ketbra}[2]{\\left\\lvert #1\\right\\rangle\\left\\langle #2\\right\\rvert}")
        lines.append("\\providecommand{\\abs}[1]{\\left\\lvert #1\\right\\rvert}")
        lines.append("\\providecommand{\\norm}[1]{\\left\\lVert #1\\right\\rVert}")
    else:
        lines.append("\\documentclass[11pt,letterpaper,fontset=fandol]{ctexart}")
        lines.append("\\usepackage{geometry}")
        lines.append("\\geometry{letterpaper, margin=1in}")
        lines.append("\\usepackage{amsmath,amssymb,amsthm}")
        lines.append("\\usepackage{mathtools}")
        lines.append("\\usepackage{amscd}")
        lines.append("\\usepackage{graphicx}")
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
        lines.append("\\providecommand{\\diag}{\\operatorname{diag}}")
        lines.append("\\providecommand{\\sgn}{\\operatorname{sgn}}")
        lines.append("\\providecommand{\\cdim}{\\operatorname{cdim}}")
        lines.append("\\providecommand{\\pcdim}{\\operatorname{pcdim}}")
        lines.append("\\providecommand{\\Den}{\\operatorname{Den}}")
        lines.append("\\providecommand{\\dashmapsto}{\\mapsto}")
        lines.append("\\providecommand{\\longtwoheadrightarrow}{\\relbar\\joinrel\\twoheadrightarrow}")
        lines.append("\\providecommand{\\Log}{\\log}")
        lines.append("\\providecommand{\\Mult}{\\operatorname{Mult}}")
        lines.append("\\providecommand{\\ket}[1]{\\left\\lvert #1\\right\\rangle}")
        lines.append("\\providecommand{\\bra}[1]{\\left\\langle #1\\right\\rvert}")
        lines.append("\\providecommand{\\braket}[1]{\\left\\langle #1\\right\\rangle}")
        lines.append("\\providecommand{\\ketbra}[2]{\\left\\lvert #1\\right\\rangle\\left\\langle #2\\right\\rvert}")
        lines.append("\\newcommand{\\abs}[1]{\\left\\lvert #1\\right\\rvert}")
        lines.append("\\newcommand{\\norm}[1]{\\left\\lVert #1\\right\\rVert}")
        lines.append("\\newcommand{\\kgref}[1]{\\ref{kg:#1}}")
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
    for p in inputs:
        lines.append(f"\\input{{{p.as_posix()}}}")
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

    if args.mode == "audit":
        if not args.root:
            raise SystemExit("--root is required for --mode audit")
        inputs, skipped = collect_tex_atoms_for_label(kg_root, args.root)
        target_name = f"audit_{args.root}"
        extra_texinputs = collect_extra_texinputs_for_labels(kg_root, {args.root})
    elif args.mode == "partial":
        if not args.label:
            raise SystemExit("--label is required for --mode partial")
        inputs, skipped = collect_tex_atoms_for_label(kg_root, args.label)
        target_name = f"partial_{args.label}"
        extra_texinputs = collect_extra_texinputs_for_labels(kg_root, {args.label})
    else:
        index_path = resolve_index_entry(kg_root, args.spec)
        spec_name = Path(args.spec).stem if args.spec else "index"
        index_labels = parse_index_labels(index_path)
        extra_texinputs = collect_extra_texinputs_for_labels(kg_root, index_labels)
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
        packed_index = build_packed_index_input(inputs[0], build_dir)
        print(f"Packed index input: {packed_index}")
        inputs = [packed_index]

    # Use absolute paths in generated main.tex to avoid relative path ambiguity.
    resolved_inputs = [Path(str(p)) for p in inputs]
    source_main_tex = discover_source_main_tex(extra_texinputs) if args.mode == "index" else None

    main_tex = build_dir / "main.tex"
    use_fragment_ref_mode = args.mode == "index" and args.index_ref_mode == "stable"
    main_tex.write_text(
        build_main_tex(
            resolved_inputs,
            fragment_ref_mode=use_fragment_ref_mode,
            degrade_cite=args.degrade_cite,
            source_main_tex=source_main_tex,
        ),
        encoding="utf-8",
    )
    if source_main_tex is not None:
        print(f"Using source preamble: {source_main_tex}")
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
