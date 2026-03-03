#!/usr/bin/env python3
"""Compile audit/index/partial views into PDF using latexmk."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path
from typing import List, Sequence, Set

from _kg_common import (
    ancestor_closure,
    default_kg_root,
    now_utc_compact,
    scan_atoms,
    tex_input_fragment_status,
    topological_order,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile KG views via latexmk.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--mode", choices=["audit", "index", "partial"], required=True)
    parser.add_argument("--root", help="Root label for audit mode")
    parser.add_argument("--label", help="Target label for partial mode")
    parser.add_argument("--spec", help="Index spec name/path for index mode")
    parser.add_argument(
        "--latexmk-cmd",
        default="latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error",
        help="latexmk command prefix",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only generate tex, do not run latexmk")
    return parser.parse_args()


def build_main_tex(inputs: Sequence[Path]) -> str:
    lines: List[str] = []
    lines.append("\\ifdefined\\pdfoutput\\pdfoutput=1\\fi")
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
    lines.append("\\providecommand{\\cdim}{\\operatorname{cdim}}")
    lines.append("\\providecommand{\\dashmapsto}{\\mapsto}")
    lines.append("\\providecommand{\\longtwoheadrightarrow}{\\relbar\\joinrel\\twoheadrightarrow}")
    lines.append("\\providecommand{\\Log}{\\log}")
    lines.append("\\newcommand{\\abs}[1]{\\left\\lvert #1\\right\\rvert}")
    lines.append("\\newcommand{\\norm}[1]{\\left\\lVert #1\\right\\rVert}")
    lines.append("\\newcommand{\\kgref}[1]{\\ref{kg:#1}}")
    lines.append("\\makeatletter")
    lines.append("\\let\\kgoriginput\\input")
    lines.append(
        "\\renewcommand{\\input}[1]{\\IfFileExists{#1}{\\kgoriginput{#1}}{\\par\\fbox{\\ttfamily missing input: \\detokenize{#1}}}}"
    )
    lines.append("\\makeatother")
    lines.append("\\begin{document}")
    for p in inputs:
        lines.append(f"\\input{{{p.as_posix()}}}")
    lines.append("\\end{document}")
    return "\n".join(lines) + "\n"


def compile_with_latexmk(build_dir: Path, main_tex: Path, latexmk_cmd: str) -> int:
    cmd = shlex.split(latexmk_cmd) + [main_tex.name]
    proc = subprocess.run(cmd, cwd=build_dir)
    return proc.returncode


def collect_tex_atoms_for_label(kg_root: Path, target_label: str) -> tuple[List[Path], List[tuple[Path, str]]]:
    atoms, scan_errors = scan_atoms(kg_root)
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


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

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
        inputs = [index_path]
        skipped = []
        spec_name = Path(args.spec).stem if args.spec else "index"
        target_name = f"index_{spec_name}"

    for skipped_path, reason in skipped:
        print(f"Skipped non-fragment TeX atom: {skipped_path} ({reason})")

    if not inputs:
        raise SystemExit("No TeX inputs selected for compile")

    build_dir = kg_root / ".kgcache" / "build" / f"{target_name}_{now_utc_compact()}"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Use absolute paths in generated main.tex to avoid relative path ambiguity.
    rel_inputs = [Path(str(p)) for p in inputs]

    main_tex = build_dir / "main.tex"
    main_tex.write_text(build_main_tex(rel_inputs), encoding="utf-8")
    print(f"Generated {main_tex}")

    if args.dry_run:
        return 0

    rc = compile_with_latexmk(build_dir, main_tex, args.latexmk_cmd)
    if rc != 0:
        print(f"latexmk failed with code {rc}")
        return rc

    print(f"Compile succeeded: {build_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
