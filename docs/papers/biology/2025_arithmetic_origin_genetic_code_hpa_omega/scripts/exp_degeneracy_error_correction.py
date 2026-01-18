# -*- coding: utf-8 -*-
"""
ISA-M3: Degeneracy as error-correction potential (Fold_6 basin metrics).

We treat the Fold_6 stable-word preimage sizes as an "error-correction potential"
available to the codon->control compilation layer.

Definitions (m=6, N in [0,63]):
  - basin_size(w) := |Fold_6^{-1}(w)|
  - For each payload class (AA; excluding Stop), under an encoding μ:
      codon_count(AA)  := # {c : Gen(c)=AA}
      unique_words(AA) := |{ w(c;μ) : Gen(c)=AA }|
      weighted_basin(AA) := Σ_{c:Gen(c)=AA} basin_size(w(c;μ))
      robustness(AA) := P(Gen(c')=AA | c' is a single-nucleotide mutation of c),
                        averaged over codons in the class.

We report correlations under μ* and compare against:
  - encoding-null: all 24 two-bit encodings
  - code-null: Monte Carlo random genetic codes preserving codon-counts (degeneracy).

Outputs:
  - sections/generated/degeneracy_error_correction.tex
  - sections/generated/degeneracy_error_correction.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BASES, GENETIC_CODE, all_encodings, fold6, fold_codon, x_m


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass(frozen=True)
class CorrSummary:
    rho: float | None
    mu_star_rank_desc: int | None
    enc_min: float | None
    enc_max: float | None
    null_mean: float | None
    null_std: float | None
    null_p_two_sided: float | None


def _mutate(codon: str, pos0: int, base: str) -> str:
    return codon[:pos0] + base + codon[pos0 + 1 :]


def _pearsonr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or not xs:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0.0 or vy <= 0.0:
        return None
    cov = sum((x - mx) * (y - my) for (x, y) in zip(xs, ys))
    return float(cov / math.sqrt(vx * vy))


def _rankdata(values: list[float]) -> list[float]:
    """
    Average ranks (1-based) with tie handling, like scipy.stats.rankdata(method="average").
    """
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while (j + 1) < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = 0.5 * ((i + 1) + (j + 1))
        for k in range(i, j + 1):
            ranks[order[k]] = float(avg)
        i = j + 1
    return ranks


def _spearmanr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or not xs:
        return None
    rx = _rankdata(xs)
    ry = _rankdata(ys)
    return _pearsonr(rx, ry)


def _empirical_p_two_sided(obs: float, nulls: list[float]) -> float:
    if not nulls:
        return float("nan")
    ge = sum(1 for r in nulls if abs(r) >= abs(obs))
    return float((ge + 1) / (len(nulls) + 1))


def _basin_sizes_m6() -> dict[str, int]:
    x6 = x_m(6)
    basin = {w: 0 for w in x6}
    for n in range(64):
        w = fold6(n)
        basin[w] = int(basin.get(w, 0)) + 1
    if sum(basin.values()) != 64:
        raise AssertionError("Basin sizes do not sum to 64.")
    return basin


def _aa_list(code: dict[str, str], *, include_stop: bool) -> list[str]:
    aas = sorted(set(code.values()))
    if include_stop:
        return aas
    return [aa for aa in aas if aa != "Stop"]


def _robustness_by_aa(code: dict[str, str]) -> dict[str, float]:
    same = Counter()
    total = Counter()
    for codon, aa0 in code.items():
        for pos0 in (0, 1, 2):
            for b in BASES:
                if b == codon[pos0]:
                    continue
                c2 = _mutate(codon, pos0, b)
                total[aa0] += 1
                if code.get(c2) == aa0:
                    same[aa0] += 1
    out = {}
    for aa0, t in total.items():
        out[aa0] = float(same.get(aa0, 0)) / float(t) if t > 0 else float("nan")
    return out


def _metrics_by_aa(
    *,
    code: dict[str, str],
    mu: dict[str, str],
    basin_size: dict[str, int],
    include_stop: bool,
) -> dict[str, dict[str, float]]:
    codons = sorted(code.keys())
    robustness = _robustness_by_aa(code)
    metrics: dict[str, dict[str, float]] = {}
    for aa in _aa_list(code, include_stop=include_stop):
        cs = [c for c in codons if code[c] == aa]
        words = [str(fold_codon(c, mu).w) for c in cs]
        metrics[aa] = {
            "codon_count": float(len(cs)),
            "unique_words": float(len(set(words))),
            "weighted_basin": float(sum(int(basin_size[w]) for w in words)),
            "robustness": float(robustness.get(aa, float("nan"))),
        }
    return metrics


def _corr_inputs(metrics: dict[str, dict[str, float]], *, exclude_stop: bool) -> dict[str, list[float]]:
    aas = sorted(metrics.keys())
    if exclude_stop:
        aas = [aa for aa in aas if aa != "Stop"]
    return {
        "codon_count": [float(metrics[aa]["codon_count"]) for aa in aas],
        "unique_words": [float(metrics[aa]["unique_words"]) for aa in aas],
        "weighted_basin": [float(metrics[aa]["weighted_basin"]) for aa in aas],
        "robustness": [float(metrics[aa]["robustness"]) for aa in aas],
    }


def _compute_corrs(metrics: dict[str, dict[str, float]]) -> dict[str, float | None]:
    x = _corr_inputs(metrics, exclude_stop=True)
    return {
        "count_vs_unique": _spearmanr(x["codon_count"], x["unique_words"]),
        "count_vs_weighted": _spearmanr(x["codon_count"], x["weighted_basin"]),
        "robust_vs_unique": _spearmanr(x["robustness"], x["unique_words"]),
        "robust_vs_weighted": _spearmanr(x["robustness"], x["weighted_basin"]),
    }


def _encoding_id(mu: dict[str, str]) -> str:
    return f"A={mu['A']},C={mu['C']},G={mu['G']},U={mu['U']}"


def _rank_desc(values: list[float], *, target: float) -> int | None:
    if not values or math.isnan(target):
        return None
    ordered = sorted(values, reverse=True)
    try:
        return int(ordered.index(target) + 1)
    except ValueError:
        return None


def _fmt_float(x: float | None, *, nd: int = 3) -> str:
    if x is None or math.isnan(float(x)):
        return "NA"
    return f"{float(x):.{int(nd)}f}"


def _fmt_p(p: float | None) -> str:
    if p is None or math.isnan(float(p)):
        return "NA"
    if float(p) < 1e-4:
        return "$<10^{-4}$"
    return f"{float(p):.4f}"


def _random_code_preserving_degeneracy(
    *, rng: random.Random, codons: list[str], degeneracy: Counter[str]
) -> dict[str, str]:
    labels: list[str] = []
    for aa in sorted(degeneracy.keys()):
        labels.extend([aa] * int(degeneracy[aa]))
    if len(labels) != len(codons):
        raise AssertionError("Degeneracy counts do not sum to 64.")
    rng.shuffle(labels)
    return {codons[i]: labels[i] for i in range(len(codons))}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ISA-M3: degeneracy as error-correction potential (Fold_6 basins).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "degeneracy_error_correction.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--n-null", type=int, default=20000, help="Number of random-code null samples (degeneracy-preserving).")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for code-null Monte Carlo.")
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)

    basin_size = _basin_sizes_m6()
    basin_hist = Counter(basin_size.values())

    cache_key: dict[str, Any] = {
        "analysis": "degeneracy_error_correction",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "n_null": int(args.n_null),
        "seed": int(args.seed),
        "out": str(out_tex),
        "basin_hist": dict(sorted((int(k), int(v)) for (k, v) in basin_hist.items())),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    # Observed metrics under μ*.
    metrics_mu_star = _metrics_by_aa(code=GENETIC_CODE, mu=MU_STAR, basin_size=basin_size, include_stop=True)
    corrs_mu_star = _compute_corrs(metrics_mu_star)

    # Encoding-null over 24 encodings (genetic code fixed).
    mu_star_id = _encoding_id(MU_STAR)
    enc_corrs: dict[str, list[tuple[str, float]]] = {k: [] for k in corrs_mu_star.keys()}
    for mu in all_encodings():
        enc_id = _encoding_id(mu)
        m = _metrics_by_aa(code=GENETIC_CODE, mu=mu, basin_size=basin_size, include_stop=True)
        c = _compute_corrs(m)
        for k, v in c.items():
            if v is None:
                continue
            enc_corrs[k].append((enc_id, float(v)))

    # Code-null (degeneracy-preserving random genetic codes) under μ*.
    rng = random.Random(int(args.seed))
    codons = sorted(GENETIC_CODE.keys())
    degeneracy = Counter(GENETIC_CODE.values())
    null_corrs: dict[str, list[float]] = {k: [] for k in corrs_mu_star.keys()}
    for _ in range(int(args.n_null)):
        code_rnd = _random_code_preserving_degeneracy(rng=rng, codons=codons, degeneracy=degeneracy)
        m = _metrics_by_aa(code=code_rnd, mu=MU_STAR, basin_size=basin_size, include_stop=True)
        c = _compute_corrs(m)
        for k, v in c.items():
            if v is None:
                continue
            null_corrs[k].append(float(v))

    # Summaries per correlation.
    summaries: dict[str, CorrSummary] = {}
    for k, rho in corrs_mu_star.items():
        r = float(rho) if rho is not None else float("nan")
        enc_pairs = enc_corrs.get(k, [])
        enc_vals = [v for (_, v) in enc_pairs]
        mu_star_val = next((v for (eid, v) in enc_pairs if eid == mu_star_id), None)
        mu_star_rank_desc = None
        if mu_star_val is not None:
            mu_star_rank_desc = int(1 + sum(1 for v in enc_vals if v > float(mu_star_val)))
        null_vals = null_corrs.get(k, [])
        summaries[k] = CorrSummary(
            rho=rho,
            mu_star_rank_desc=mu_star_rank_desc,
            enc_min=min(enc_vals) if enc_vals else None,
            enc_max=max(enc_vals) if enc_vals else None,
            null_mean=statistics.mean(null_vals) if null_vals else None,
            null_std=statistics.pstdev(null_vals) if len(null_vals) >= 2 else None,
            null_p_two_sided=_empirical_p_two_sided(r, null_vals) if null_vals and (rho is not None) else None,
        )

    # Emit LaTeX.
    basin_hist_s = ", ".join(f"{int(k)}:{int(v)}" for (k, v) in sorted(basin_hist.items()))
    lines: list[str] = []
    lines.append("\\paragraph{ISA-M3: Degeneracy as error-correction potential (Fold$_6$ basins).}")
    lines.append(
        "Define basin size $|\\mathrm{Fold}_6^{-1}(w)|$ over $N\\in\\{0,\\dots,63\\}$ (histogram "
        f"$\\{{{basin_hist_s}\\}}$, sum=64). For each amino acid payload class (excluding Stop) under $\\mu^\\ast$, "
        "compute: codon degeneracy (\\#codons), unique Fold$_6$ words, weighted basin $\\sum \\lvert\\mathrm{Fold}_6^{-1}(w)\\rvert$, "
        "and point-mutation robustness (fraction of single-nucleotide mutations that preserve the payload AA)."
    )
    lines.append("")

    # AA-level table under μ*.
    aas_all = sorted(metrics_mu_star.keys())
    aas = [aa for aa in aas_all if aa != "Stop"]
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{l r r r r}")
    lines.append("\\toprule")
    lines.append("AA & \\#codons & unique $w$ & weighted basin & robustness \\\\")
    lines.append("\\midrule")
    for aa in aas:
        m = metrics_mu_star[aa]
        lines.append(
            f"{aa} & {int(m['codon_count']):d} & {int(m['unique_words']):d} & {int(m['weighted_basin']):d} & {_fmt_float(m['robustness'], nd=3)} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # Correlation summary table.
    def row(label: str, key: str) -> str:
        s = summaries[key]
        return (
            f"{label} & {_fmt_float(s.rho, nd=3)} & "
            f"{('NA' if s.mu_star_rank_desc is None else str(int(s.mu_star_rank_desc)) + '/24')} & "
            f"{_fmt_float(s.enc_min, nd=3)} & {_fmt_float(s.enc_max, nd=3)} & "
            f"{_fmt_float(s.null_mean, nd=3)}$\\pm${_fmt_float(s.null_std, nd=3)} & "
            f"{_fmt_p(s.null_p_two_sided)} \\\\"
        )

    lines.append("\\noindent Correlation summary (Spearman $\\rho$; AA classes only):")
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{5pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{l r r r r r r}")
    lines.append("\\toprule")
    lines.append("pair & $\\rho(\\mu^\\ast)$ & rank$_{24}$ & min$_{24}$ & max$_{24}$ & null mean$\\pm$sd & $p_{\\mathrm{null}}$ \\\\")
    lines.append("\\midrule")
    lines.append(row("degeneracy vs unique $w$", "count_vs_unique"))
    lines.append(row("degeneracy vs weighted basin", "count_vs_weighted"))
    lines.append(row("robustness vs unique $w$", "robust_vs_unique"))
    lines.append(row("robustness vs weighted basin", "robust_vs_weighted"))
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append(
        f"\\noindent Null details: encoding-null over 24 two-bit encodings; code-null is {int(args.n_null)} "
        f"degeneracy-preserving random codes (seed={int(args.seed)}), two-sided empirical $p$."
    )
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()
