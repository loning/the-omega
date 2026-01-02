# -*- coding: utf-8 -*-
"""
Cross-resolution stability of Fold_m codon-usage null deviations on the corpus panel.

We reuse the already-scanned corpus panel JSON summary (codon_counts, aa_counts),
so no FASTA rescanning is required.

For each dataset item i and each m, we compute:
  diff_u(i,m) = \bar{U}_obs - E[\bar{U}]   under AA-preserving null,
where U_m is codon-scale uplift (Delta_m under mu*).

We then summarize stability across m by reporting pairwise correlations across datasets:
  - Pearson r on diff_u(·,m)
  - Spearman rho on ranks of diff_u(·,m)
  - sign-agreement rate across datasets

Note: Any m with zero variance across datasets (e.g., saturating m>=9 where U_m ≡ 0)
is excluded from correlation calculations.

Outputs:
  - sections/generated/foldm_corpus_panel_codon_usage_null_u_stability_summary.tex
  - sections/generated/foldm_corpus_panel_codon_usage_null_u_stability_table.tex
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
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


def _fmt_float(x: object, *, nd: int = 3) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}"


def _fmt_float_signed(x: object, *, nd: int = 3) -> str:
    if not _is_num(x):
        return "-"
    v = float(x)
    s = f"{v:.{int(nd)}f}"
    return s if s.startswith("-") else ("+" + s)


def _sign(x: float, *, eps: float = 1e-15) -> int:
    if abs(float(x)) <= float(eps):
        return 0
    return 1 if float(x) > 0 else -1


def _pearsonr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys):
        raise ValueError("length mismatch")
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / float(n)
    my = sum(ys) / float(n)
    sxx = 0.0
    syy = 0.0
    sxy = 0.0
    for x, y in zip(xs, ys):
        dx = float(x) - mx
        dy = float(y) - my
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy
    if sxx <= 0.0 or syy <= 0.0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _rankdata(values: list[float]) -> list[float]:
    """
    Average ranks for ties. Ranks are 1..n.
    """
    n = len(values)
    pairs = [(float(v), i) for i, v in enumerate(values)]
    pairs.sort(key=lambda x: x[0])
    ranks = [0.0] * n
    i = 0
    rank = 1
    while i < n:
        j = i + 1
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        # tie group i..j-1, ranks rank..rank+(j-i)-1
        r_lo = rank
        r_hi = rank + (j - i) - 1
        r_avg = 0.5 * (float(r_lo) + float(r_hi))
        for k in range(i, j):
            _v, idx = pairs[k]
            ranks[idx] = r_avg
        rank += (j - i)
        i = j
    return ranks


def _spearmanr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys):
        raise ValueError("length mismatch")
    if len(xs) < 2:
        return None
    rx = _rankdata(xs)
    ry = _rankdata(ys)
    return _pearsonr(rx, ry)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-resolution stability of Fold_m codon-usage null deviations (corpus panel).")
    p.add_argument("--panel-json", default=str(default_panel_json()), help="Input corpus panel JSON summary.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated Fold_m window lengths to evaluate.")
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "foldm_corpus_panel_codon_usage_null_u_stability_table.tex"),
        help="Output LaTeX table fragment path.",
    )
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "foldm_corpus_panel_codon_usage_null_u_stability_summary.tex"),
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

    if not panel_json.exists():
        raise SystemExit(f"Missing panel JSON: {panel_json}")

    cache_key = {
        "analysis": "foldm_corpus_panel_codon_usage_null_u_stability",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(x) for x in m_list],
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

    # Collect per-dataset vectors.
    dataset_keys: list[tuple[str, str]] = []  # (domain,label)
    diff_u_by_m: dict[int, list[float]] = {int(m): [] for m in m_list}

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
        if code_id not in tt:
            continue
        codon_to_aa, _stops = tt[code_id]
        codons_by_aa = codons_by_aa_from_map(codon_to_aa)
        aa_counts_i = {str(k): int(v) for k, v in aa_counts.items()}
        codon_counts_i = {str(k): int(v) for k, v in codon_counts.items()}

        # Compute diff_u for each m; require all m to be present for the dataset to be included.
        vals: dict[int, float] = {}
        ok = True
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
                ok = False
                break
            vals[int(m)] = float(de_u.obs_mean - de_u.null_mean)
        if not ok:
            continue

        dataset_keys.append((domain, label))
        for m in m_list:
            diff_u_by_m[int(m)].append(float(vals[int(m)]))

    n_items = len(dataset_keys)
    if n_items < 2:
        raise SystemExit("Not enough panel items to compute stability (need >=2).")

    # Filter m with nonzero variance across datasets.
    usable_m: list[int] = []
    for m in m_list:
        xs = diff_u_by_m[int(m)]
        if len(xs) != n_items:
            continue
        mx = sum(xs) / float(n_items)
        var = sum((x - mx) ** 2 for x in xs) / float(n_items)
        if var > 0.0:
            usable_m.append(int(m))

    # Compute pairwise metrics.
    rows: list[dict[str, object]] = []
    for m1, m2 in combinations(usable_m, 2):
        x = diff_u_by_m[int(m1)]
        y = diff_u_by_m[int(m2)]
        r = _pearsonr(x, y)
        rho = _spearmanr(x, y)
        agree = sum(1 for a, b in zip(x, y) if _sign(a) == _sign(b))
        rows.append(
            {
                "m1": int(m1),
                "m2": int(m2),
                "n": int(n_items),
                "pearson_r": r,
                "spearman_rho": rho,
                "sign_agree": int(agree),
                "sign_rate": float(agree) / float(n_items),
            }
        )

    # Summary string.
    m_in = ",".join(str(int(m)) for m in m_list)
    m_use = ",".join(str(int(m)) for m in usable_m)
    s = (
        "Cross-resolution stability of corpus-panel codon-usage null deviations for uplift $\\Delta\\overline{U}$ "
        f"(Pearson/Spearman across datasets; input $m\\in\\{{{m_in}\\}}$; usable $m\\in\\{{{m_use}\\}}$; $n={n_items}$ panel items)."
    )
    write_text_atomic(out_summary, s + "\n")

    # LaTeX table.
    rows.sort(key=lambda r: (int(r["m1"]), int(r["m2"])))
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r r r r r r}")
    lines.append("\\toprule")
    lines.append("$m_1$ & $m_2$ & $n$ & Pearson $r$ & Spearman $\\rho$ & sign-agree \\\\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(
            f"{int(r['m1'])} & {int(r['m2'])} & {int(r['n'])} & {_fmt_float(r['pearson_r'], nd=3)} & {_fmt_float(r['spearman_rho'], nd=3)} & "
            f"{int(r['sign_agree'])}/{int(r['n'])} ({_fmt_float(100.0*float(r['sign_rate']), nd=1)}\\%) \\\\"
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


