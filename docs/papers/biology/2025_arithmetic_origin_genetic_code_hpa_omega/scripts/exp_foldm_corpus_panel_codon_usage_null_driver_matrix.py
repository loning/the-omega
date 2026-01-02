# -*- coding: utf-8 -*-
"""
Fold_m codon-usage null deviations (uplift U) on the corpus panel: driver matrix.

For each dataset and each m, we report:
  - diff_u = \bar{U}_obs - E[\bar{U}] under the AA-preserving null
  - top-K amino-acid contributions (from aa_preserving_null_decomposition)
  - top-K codon contributions (from aa_preserving_null_decomposition)

This complements:
  - foldm_corpus_panel_codon_usage_null_u_table.tex (aggregate diff_u per m)
  - corpus_panel_codon_usage_null_decomp_u_* (detailed m=6 decomposition)

No FASTA rescanning is required; inputs come from data/panel/corpus_panel_summary.json.

Outputs:
  - sections/generated/foldm_corpus_panel_codon_usage_null_u_driver_matrix_summary.tex
  - sections/generated/foldm_corpus_panel_codon_usage_null_u_driver_matrix_table.tex
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from exp_corpus_panel import codons_by_aa_from_map, load_translation_tables
from genetic_code_tools import GENETIC_CODE, fold_codon_m
from stats_tools import aa_preserving_null_decomposition


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_panel_json() -> Path:
    return root_dir() / "data" / "panel" / "corpus_panel_summary.json"


def _file_fingerprint(path: Path) -> dict[str, object]:
    st = path.stat()
    return {
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _parse_int_list(s: str) -> list[int]:
    out: list[int] = []
    for p in str(s or "").split(","):
        p = p.strip()
        if not p:
            continue
        out.append(int(p))
    out = sorted({int(x) for x in out if int(x) > 0})
    if not out:
        raise SystemExit("--m-list must contain positive integers")
    return out


def _is_num(x: object) -> bool:
    try:
        v = float(x)  # type: ignore[arg-type]
    except Exception:
        return False
    return (not math.isnan(v)) and math.isfinite(v)


def _fmt_float(x: object, *, nd: int = 4) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}"


def _fmt_float_signed(x: object, *, nd: int = 4) -> str:
    if not _is_num(x):
        return "-"
    v = float(x)
    s = f"{v:.{int(nd)}f}"
    return s if s.startswith("-") else ("+" + s)


def _escape_tex(s: str) -> str:
    return str(s).replace("_", "\\_")


def _fmt_aa_drivers(de_u: object, *, k: int, nd: int = 4) -> str:
    # type: ignore[attr-defined]
    aa_contribs = list(de_u.aa_contribs)  # type: ignore[attr-defined]
    parts: list[str] = []
    for r in aa_contribs[: int(k)]:
        parts.append(f"{r.aa}({_fmt_float_signed(r.contrib, nd=nd)})")
    return ", ".join(parts) if parts else "-"


def _fmt_codon_drivers(de_u: object, *, k: int, nd: int = 4) -> str:
    # type: ignore[attr-defined]
    codon_contribs = list(de_u.codon_contribs)  # type: ignore[attr-defined]
    parts: list[str] = []
    for r in codon_contribs[: int(k)]:
        parts.append(f"{r.codon}({r.aa},{_fmt_float_signed(r.contrib, nd=nd)})")
    return ", ".join(parts) if parts else "-"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m corpus panel uplift deviation driver matrix (AA/codon contributions).")
    p.add_argument("--panel-json", default=str(default_panel_json()), help="Input corpus panel JSON summary.")
    p.add_argument("--m-list", default="6,7,8", help="Comma-separated Fold_m window lengths to evaluate (recommend <=8).")
    p.add_argument("--top-k", type=int, default=3, help="Top-k AA and codon contributors to report.")
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "foldm_corpus_panel_codon_usage_null_u_driver_matrix_table.tex"),
        help="Output LaTeX table fragment path.",
    )
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "foldm_corpus_panel_codon_usage_null_u_driver_matrix_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    panel_json = Path(args.panel_json)
    out_table = Path(args.out_table)
    out_summary = Path(args.out_summary)
    m_list = _parse_int_list(str(args.m_list))
    top_k = int(args.top_k)
    if top_k < 1:
        raise SystemExit("--top-k must be >= 1")

    if not panel_json.exists():
        raise SystemExit(f"Missing panel JSON: {panel_json}")

    cache_key = {
        "analysis": "foldm_corpus_panel_codon_usage_null_u_driver_matrix",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(x) for x in m_list],
        "top_k": int(top_k),
        "mu_star": MU_STAR,
        "panel_json": _file_fingerprint(panel_json),
        "out_table": str(out_table),
        "out_summary": str(out_summary),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_table, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_table}", flush=True)
        return

    panel = json.loads(panel_json.read_text(encoding="utf-8"))
    if not isinstance(panel, dict):
        raise SystemExit("Panel JSON malformed (expected dict).")
    items = panel.get("items") or []
    if not isinstance(items, list):
        raise SystemExit("Panel JSON malformed (missing items list).")

    # Precompute codon-level Delta_m under mu* for each m.
    delta_m: dict[int, dict[str, float]] = {}
    for m in m_list:
        delta_m[int(m)] = {}
        for codon in GENETIC_CODE:
            delta_m[int(m)][codon] = float(fold_codon_m(codon, MU_STAR, m=int(m)).delta)

    tt = load_translation_tables()

    rows: list[dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if not it.get("present"):
            continue
        label = str(it.get("label") or "-")
        domain = str(it.get("domain") or "-")
        code_id = int(it.get("code_id") or 1)
        summ = it.get("summary") or {}
        if not isinstance(summ, dict):
            continue
        codon_counts = summ.get("codon_counts") or {}
        aa_counts = summ.get("aa_counts") or {}
        if not isinstance(codon_counts, dict) or not isinstance(aa_counts, dict):
            continue
        n = int(summ.get("coding_tokens", 0) or 0)
        if code_id not in tt:
            continue
        codon_to_aa, _stops = tt[code_id]
        codons_by_aa = codons_by_aa_from_map(codon_to_aa)

        aa_counts_i = {str(k): int(v) for k, v in aa_counts.items()}
        codon_counts_i = {str(k): int(v) for k, v in codon_counts.items()}

        for m in m_list:
            try:
                de_u = aa_preserving_null_decomposition(
                    aa_counts=aa_counts_i,
                    codon_counts=codon_counts_i,
                    codons_by_aa=codons_by_aa,
                    genetic_code=codon_to_aa,
                    codon_value=delta_m[int(m)],
                    exclude_aas={"Stop"},
                )
            except Exception:
                continue
            diff_u = float(de_u.obs_mean - de_u.null_mean)
            rows.append(
                {
                    "m": int(m),
                    "label": label,
                    "domain": domain,
                    "code_id": int(code_id),
                    "n": int(n),
                    "diff_u": diff_u,
                    "aa_drivers": _fmt_aa_drivers(de_u, k=top_k, nd=4),
                    "codon_drivers": _fmt_codon_drivers(de_u, k=top_k, nd=4),
                }
            )

    m_str = ",".join(str(int(m)) for m in m_list)
    s = (
        f"Fold$_m$ corpus-panel uplift deviation driver matrix for $\\Delta\\overline{{U}}$ "
        f"(top-{top_k} AA and codon contributors; $m\\in\\{{{m_str}\\}}$)."
    )
    write_text_atomic(out_summary, s + "\n")

    rows.sort(key=lambda r: (int(r["m"]), str(r["domain"]), str(r["label"])))

    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r l l r r r l l}")
    lines.append("\\toprule")
    lines.append("$m$ & label & domain & code id & $n$ & $\\Delta\\overline{U}$ & top AA & top codons \\\\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(
            f"{int(r['m'])} & \\path{{{_escape_tex(str(r['label']))}}} & {r['domain']} & {int(r['code_id'])} & {int(r['n'])} & "
            f"{_fmt_float_signed(r['diff_u'], nd=4)} & {_escape_tex(str(r['aa_drivers']))} & {_escape_tex(str(r['codon_drivers']))} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")

    write_text_atomic(out_table, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_table), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_table)


if __name__ == "__main__":
    main()


