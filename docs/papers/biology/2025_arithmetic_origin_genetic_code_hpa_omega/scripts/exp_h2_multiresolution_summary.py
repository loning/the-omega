# -*- coding: utf-8 -*-
"""
Compact H2 multi-resolution (Fold_m) sensitivity summary.

This script produces a small LaTeX fragment that summarizes how a key H2 endpoint
behaves as a function of m, using the already-generated eukaryotic RefSeq meta-analysis
table (foldm_stop_context_meta_eukaryota).

Outputs:
  - sections/generated/h2_multiresolution_summary.tex
  - sections/generated/h2_multiresolution_summary.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic


SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fingerprint(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"name": str(path), "missing": True}
    st = path.stat()
    return {
        "name": path.name,
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _fib(n: int) -> int:
    if n <= 0:
        return 0
    a, b = 1, 1
    if n == 1:
        return 1
    if n == 2:
        return 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


@dataclass(frozen=True)
class MetaRow:
    m: int
    side: str
    pair: str
    k: int
    n: int
    meta_diff: float
    meta_se: float
    z: float
    p_text: str


_ROW_RE = re.compile(
    r"^\s*(\d+)\s*&\s*(after|before)\s*&\s*(.+?)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*([\-0-9.]+)\s*&\s*([\-0-9.]+)\s*&\s*([\-0-9.]+)\s*&\s*([^\\\\]+)\\\\\s*$"
)


def parse_meta_table(tex: str) -> list[MetaRow]:
    rows: list[MetaRow] = []
    for line in tex.splitlines():
        m = _ROW_RE.match(line)
        if not m:
            continue
        rows.append(
            MetaRow(
                m=int(m.group(1)),
                side=str(m.group(2)),
                pair=str(m.group(3)).strip(),
                k=int(m.group(4)),
                n=int(m.group(5)),
                meta_diff=float(m.group(6)),
                meta_se=float(m.group(7)),
                z=float(m.group(8)),
                p_text=str(m.group(9)).strip(),
            )
        )
    return rows


def _fmt_float(x: float | None, *, nd: int = 4) -> str:
    if x is None:
        return "-"
    return f"{x:.{int(nd)}f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="H2 multi-resolution summary fragment generator")
    p.add_argument(
        "--src-tex",
        default=str(generated_dir() / "foldm_stop_context_meta_eukaryota.tex"),
        help="Source meta-analysis LaTeX table to summarize.",
    )
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "h2_multiresolution_summary.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    src = Path(args.src_tex)
    out_tex = Path(args.out_tex)

    cache_key: dict[str, Any] = {
        "analysis": "h2_multiresolution_summary",
        "version": int(SCRIPT_VERSION),
        "src": str(src),
        "src_fingerprint": _fingerprint(src),
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    if not src.exists():
        raise SystemExit(f"Missing source file: {src}")

    rows = parse_meta_table(src.read_text(encoding="utf-8"))
    if not rows:
        raise SystemExit(f"No parseable rows found in: {src}")

    # Focus endpoint: UAA vs UGA at k=10, report after/before and implied Δ contrast.
    focus_pair = "UAA$\\,$vs$\\,$UGA"
    focus_k = 10

    by_m: dict[int, dict[str, MetaRow]] = {}
    for r in rows:
        if r.pair != focus_pair or r.k != focus_k:
            continue
        by_m.setdefault(int(r.m), {})[str(r.side)] = r

    ms = [6, 7, 8, 9]
    table_rows: list[str] = []
    for m in ms:
        ra = by_m.get(int(m), {}).get("after")
        rb = by_m.get(int(m), {}).get("before")
        diff_after = ra.meta_diff if ra is not None else None
        diff_before = rb.meta_diff if rb is not None else None
        diff_delta = (diff_after - diff_before) if (diff_after is not None and diff_before is not None) else None

        # Resolution bookkeeping (deterministic): |X_m|=F_{m+2}, |X_m^bdry|=F_{m-2} for m>=4.
        xm = _fib(m + 2)
        bsz = _fib(m - 2) if m >= 4 else 0

        note = ""
        if ra is None and rb is None:
            note = "degenerate on codon-scale $N\\le 63$"
        table_rows.append(
            f"{m} & {xm} & {bsz} & {_fmt_float(diff_before)} & {_fmt_float(diff_after)} & {_fmt_float(diff_delta)} & {note} \\\\"
        )

    lines: list[str] = []
    lines.append(
        "Fold$_m$ sensitivity snapshot for a key H2 endpoint (Eukaryota RefSeq mRNA meta-analysis; best ORF; pair UAA vs UGA; $k=10$)."
    )
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r r r r r r l}")
    lines.append("\\toprule")
    lines.append("$m$ & $|X_m|$ & $|X_m^{\\mathrm{bdry}}|$ & diff(before) & diff(after) & diff($\\Delta$) & note \\\\")
    lines.append("\\midrule")
    lines.extend(table_rows)
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")
    lines.append(
        "\\noindent Here ``diff(after)'' denotes the fixed-effect meta difference of mean uplift windows "
        "($\\overline{U}_{\\mathrm{after}}$) between UAA and UGA terminal stops, and ``diff($\\Delta$)'' is the implied "
        "contrast on $\\Delta U=U_{\\mathrm{after}}-U_{\\mathrm{before}}$ via diff(after)$-$diff(before)."
    )
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()

