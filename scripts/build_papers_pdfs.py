#!/usr/bin/env python3
"""
Build and verify `docs/papers/**/main.pdf` for CI and local use.

This script is designed to:
  - Compute stable content hashes for paper sources (excluding build artifacts).
  - Plan which papers need rebuild (missing PDF or source hash mismatch).
  - Build planned papers using `latexmk` with an engine fallback chain.
  - Write per-paper source-hash stamps under `.ci_cache/papers/**/sources.sha256`.
  - Verify that every `main.tex` has a corresponding `main.pdf`.

All output is in English.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import shorten
from typing import Iterable


EXCLUDE_NAMES = {"main.pdf"}
EXCLUDE_SUFFIXES = {
    ".acn",
    ".acr",
    ".alg",
    ".aux",
    ".bbl",
    ".bcf",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".glo",
    ".glg",
    ".gls",
    ".idx",
    ".ilg",
    ".ind",
    ".ist",
    ".lof",
    ".log",
    ".lot",
    ".nav",
    ".out",
    ".snm",
    ".synctex",
    ".toc",
    ".vrb",
    ".xdv",
}


@dataclass(frozen=True)
class PlanItem:
    paper_dir: Path
    sources_hash: str


def _iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name in EXCLUDE_NAMES:
            continue
        if p.name.endswith(".synctex.gz"):
            continue
        if p.name.endswith(".run.xml"):
            continue
        if p.suffix in EXCLUDE_SUFFIXES:
            continue
        if "__pycache__" in p.parts:
            continue
        files.append(p)
    files.sort(key=lambda x: str(x.relative_to(root)))
    return files


def _hash_files(base: Path, files: Iterable[Path]) -> str:
    h = hashlib.sha256()
    for p in files:
        rel = p.relative_to(base)
        h.update(str(rel).encode("utf-8"))
        h.update(b"\0")
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def compute_sources_hash(paper_dir: Path) -> str:
    return _hash_files(paper_dir, _iter_source_files(paper_dir))


def compute_papers_cache_key(papers_root: Path) -> str:
    if not papers_root.exists():
        return "no-papers"
    return _hash_files(papers_root, _iter_source_files(papers_root))


def find_paper_dirs(papers_root: Path) -> list[Path]:
    if not papers_root.exists():
        return []
    return sorted({p.parent for p in papers_root.rglob("main.tex")}, key=lambda p: str(p))


def stamp_path(stamp_root: Path, papers_root: Path, paper_dir: Path) -> Path:
    rel = paper_dir.relative_to(papers_root)
    return stamp_root / rel / "sources.sha256"


def read_stamp(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def write_stamp(path: Path, sources_hash: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sources_hash + "\n", encoding="utf-8")


def write_plan_file(plan_file: Path, items: list[PlanItem]) -> None:
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    if not items:
        plan_file.write_text("", encoding="utf-8")
        return
    plan_file.write_text(
        "".join(f"{item.paper_dir}\t{item.sources_hash}\n" for item in items),
        encoding="utf-8",
    )


def read_plan_file(plan_file: Path) -> list[PlanItem]:
    if not plan_file.exists():
        return []
    items: list[PlanItem] = []
    for raw in plan_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "\t" not in line:
            raise ValueError(f"Invalid plan line (expected tab separator): {raw!r}")
        paper_dir_s, sources_hash = line.split("\t", 1)
        items.append(PlanItem(Path(paper_dir_s), sources_hash.strip()))
    return items


def plan_rebuilds(papers_root: Path, stamp_root: Path) -> tuple[list[Path], list[PlanItem]]:
    stamp_root.mkdir(parents=True, exist_ok=True)

    paper_dirs = find_paper_dirs(papers_root)
    to_build: list[PlanItem] = []

    for d in paper_dirs:
        current = compute_sources_hash(d)
        cached = read_stamp(stamp_path(stamp_root, papers_root, d))
        pdf_path = d / "main.pdf"
        if (not pdf_path.exists()) or (cached != current):
            to_build.append(PlanItem(d, current))

    return paper_dirs, to_build


def _run_latexmk(paper_dir: Path) -> None:
    cmds = [
        ["latexmk", "-quiet", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex"],
        ["latexmk", "-quiet", "-pdfxe", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex"],
        ["latexmk", "-quiet", "-pdflua", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "main.tex"],
    ]

    last_rc: int | None = None
    for cmd in cmds:
        proc = subprocess.run(cmd, cwd=str(paper_dir))
        last_rc = proc.returncode
        if proc.returncode == 0:
            return

    raise RuntimeError(f"latexmk failed in {paper_dir} (last exit code: {last_rc})")


def _clean_latexmk(paper_dir: Path) -> None:
    # Keep the final PDF; remove auxiliary build artifacts to save disk space in CI.
    subprocess.run(["latexmk", "-c"], cwd=str(paper_dir))


def build_from_plan(
    papers_root: Path,
    stamp_root: Path,
    plan_items: list[PlanItem],
    *,
    clean: bool,
) -> None:
    for item in plan_items:
        paper_dir = item.paper_dir
        sources_hash = item.sources_hash

        print(f"Building: {paper_dir}")
        try:
            _run_latexmk(paper_dir)
        except Exception as e:
            log_path = paper_dir / "main.log"
            print(f"Build failed in: {paper_dir}", file=sys.stderr)
            print(f"Error: {shorten(str(e), width=500)}", file=sys.stderr)
            if log_path.exists():
                try:
                    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    tail = lines[-200:] if len(lines) > 200 else lines
                    print("---- main.log (tail) ----", file=sys.stderr)
                    for line in tail:
                        print(line, file=sys.stderr)
                    print("---- end main.log ----", file=sys.stderr)
                except Exception as log_e:
                    print(f"Could not read log file {log_path}: {log_e}", file=sys.stderr)
            else:
                print(f"Log file not found: {log_path}", file=sys.stderr)
            raise

        pdf_path = paper_dir / "main.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError(f"Expected PDF not found: {pdf_path}")

        write_stamp(stamp_path(stamp_root, papers_root, paper_dir), sources_hash)
        if clean:
            _clean_latexmk(paper_dir)


def verify_all_pdfs(papers_root: Path) -> None:
    if not papers_root.exists():
        print("No papers directory found; nothing to verify.")
        return

    missing: list[Path] = []
    for tex in papers_root.rglob("main.tex"):
        pdf = tex.parent / "main.pdf"
        if not pdf.exists():
            missing.append(pdf)

    if missing:
        for p in missing:
            print(f"Missing PDF: {p}", file=sys.stderr)
        raise FileNotFoundError(f"Missing {len(missing)} PDF(s) under {papers_root}")


def write_github_output(pairs: dict[str, str]) -> None:
    out_path = os.environ.get("GITHUB_OUTPUT")
    if not out_path:
        raise RuntimeError("GITHUB_OUTPUT is not set; cannot write GitHub Actions outputs.")
    with open(out_path, "a", encoding="utf-8") as f:
        for k, v in pairs.items():
            f.write(f"{k}={v}\n")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build and verify docs/papers PDFs.")
    parser.add_argument("--papers-root", default="docs/papers", help="Path to papers root directory.")
    parser.add_argument("--stamp-root", default=".ci_cache/papers", help="Path to stamp cache directory.")
    parser.add_argument(
        "--plan-file",
        default=".ci_cache/papers_to_build.tsv",
        help="Path to plan file used between plan/build steps.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_key = sub.add_parser("cache-key", help="Print a stable cache key hash for papers sources.")
    p_key.add_argument("--github-output", action="store_true", help="Also write `hash` to $GITHUB_OUTPUT.")

    p_plan = sub.add_parser("plan", help="Plan which papers need rebuild and write a plan file.")
    p_plan.add_argument("--github-output", action="store_true", help="Also write counts to $GITHUB_OUTPUT.")

    p_build = sub.add_parser("build", help="Build papers PDFs based on the plan file (or recompute if missing).")
    p_build.add_argument(
        "--replan-if-missing",
        action="store_true",
        help="If plan file is missing, recompute the plan instead of failing.",
    )
    clean_default = os.environ.get("CI", "").lower() in {"1", "true", "yes", "on"}
    clean_group = p_build.add_mutually_exclusive_group()
    clean_group.add_argument("--clean", dest="clean", action="store_true", help="Clean LaTeX aux files after build.")
    clean_group.add_argument("--no-clean", dest="clean", action="store_false", help="Do not clean LaTeX aux files.")
    p_build.set_defaults(clean=clean_default)

    sub.add_parser("verify", help="Verify all papers have main.pdf.")

    args = parser.parse_args(argv)

    papers_root = Path(args.papers_root)
    stamp_root = Path(args.stamp_root)
    plan_file = Path(args.plan_file)

    if args.cmd == "cache-key":
        key = compute_papers_cache_key(papers_root)
        print(key)
        if args.github_output:
            write_github_output({"hash": key})
        return 0

    if args.cmd == "plan":
        paper_dirs, to_build = plan_rebuilds(papers_root, stamp_root)
        write_plan_file(plan_file, to_build)
        print(f"Found {len(paper_dirs)} paper(s); need rebuild: {len(to_build)}")
        if args.github_output:
            write_github_output(
                {
                    "papers_total": str(len(paper_dirs)),
                    "papers_to_build": str(len(to_build)),
                }
            )
        return 0

    if args.cmd == "build":
        if not plan_file.exists():
            if not args.replan_if_missing:
                raise FileNotFoundError(
                    f"Plan file not found: {plan_file}. Run `plan` first or pass --replan-if-missing."
                )
            _, to_build = plan_rebuilds(papers_root, stamp_root)
            plan_items = to_build
        else:
            plan_items = read_plan_file(plan_file)

        if not plan_items:
            print("No papers to build.")
            return 0

        build_from_plan(papers_root, stamp_root, plan_items, clean=bool(getattr(args, "clean", False)))
        return 0

    if args.cmd == "verify":
        verify_all_pdfs(papers_root)
        print("All papers PDFs exist.")
        return 0

    raise AssertionError(f"Unhandled command: {args.cmd}")


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        raise SystemExit(130)


