# -*- coding: utf-8 -*-
"""
Stability of recoding discrimination AUC across Fold_m (standard library only).

We parse the LaTeX fragment produced by:
  - scripts/exp_recoding_discrimination_foldm.py
and quantify cross-m concordance across the task set (comparison x metric).

For each task t and m we have an AUC(t,m). We analyze delta(t,m)=AUC(t,m)-0.5:
  - Pearson r and Spearman rho across tasks between m1 and m2
  - sign agreement rate for delta(t,m)
  - list tasks with sign flips (delta changes sign) between m1 and m2

Outputs:
  - sections/generated/recoding_discrimination_foldm_stability_summary.tex
  - sections/generated/recoding_discrimination_foldm_stability_table.tex
  - sections/generated/recoding_discrimination_foldm_stability_flips.tex
"""

from __future__ import annotations

import argparse
import math
import re
from itertools import combinations
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic


SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_in_tex() -> Path:
    return generated_dir() / "recoding_discrimination_summary_foldm.tex"


def _file_fingerprint(path: Path) -> dict[str, object]:
    st = path.stat()
    return {
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


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


def _fmt_percent(x: object, *, nd: int = 1) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}\\%"


def _sign(x: float, *, eps: float = 1e-12) -> int:
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


ROW_RE = re.compile(r"^\s*(\d+)\s*&\s*(.*?)\s*&\s*(.*?)\s*&\s*(\d+)\s*&\s*(\d+)\s*&\s*([0-9.]+)\s*\[")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stability of recoding discrimination AUC across Fold_m (parse LaTeX).")
    p.add_argument("--in-tex", default=str(default_in_tex()), help="Input LaTeX fragment (recoding_discrimination_summary_foldm.tex).")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "recoding_discrimination_foldm_stability_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "recoding_discrimination_foldm_stability_table.tex"),
        help="Output LaTeX table fragment path.",
    )
    p.add_argument(
        "--out-flips",
        default=str(generated_dir() / "recoding_discrimination_foldm_stability_flips.tex"),
        help="Output LaTeX flips fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    in_tex = Path(args.in_tex)
    out_summary = Path(args.out_summary)
    out_table = Path(args.out_table)
    out_flips = Path(args.out_flips)

    if not in_tex.exists():
        raise SystemExit(f"Missing input: {in_tex}")

    cache_key = {
        "analysis": "recoding_discrimination_foldm_stability",
        "version": int(SCRIPT_VERSION),
        "in_tex": _file_fingerprint(in_tex),
        "out_summary": str(out_summary),
        "out_table": str(out_table),
        "out_flips": str(out_flips),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_table, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_table}", flush=True)
        return

    # task -> m -> auc
    auc_by_task: dict[tuple[str, str], dict[int, float]] = {}
    all_m: set[int] = set()
    with in_tex.open("r", encoding="utf-8") as f:
        for line in f:
            m = ROW_RE.match(line)
            if not m:
                continue
            m_i = int(m.group(1))
            comp = str(m.group(2)).strip()
            metric = str(m.group(3)).strip()
            auc = float(m.group(6))
            key = (comp, metric)
            auc_by_task.setdefault(key, {})[m_i] = float(auc)
            all_m.add(int(m_i))

    if not auc_by_task:
        raise SystemExit(f"No AUC rows parsed from: {in_tex}")

    ms = sorted(all_m)
    tasks = sorted(auc_by_task.keys(), key=lambda t: (t[0], t[1]))

    # Keep only tasks with complete m coverage.
    complete_tasks: list[tuple[str, str]] = []
    for t in tasks:
        if all(int(m) in auc_by_task[t] for m in ms):
            complete_tasks.append(t)
    tasks = complete_tasks
    if len(tasks) < 2:
        raise SystemExit("Not enough complete tasks to compute stability (need >=2).")

    # Usable m: nonzero variance in delta=AUC-0.5 across tasks.
    usable_ms: list[int] = []
    for m in ms:
        deltas = [float(auc_by_task[t][int(m)]) - 0.5 for t in tasks]
        mu = sum(deltas) / float(len(deltas))
        var = sum((x - mu) ** 2 for x in deltas) / float(len(deltas))
        if var > 0.0:
            usable_ms.append(int(m))

    # Pairwise stability metrics.
    stab_rows: list[dict[str, object]] = []
    flip_rows: list[dict[str, object]] = []
    for m1, m2 in combinations(usable_ms, 2):
        x = [float(auc_by_task[t][m1]) - 0.5 for t in tasks]
        y = [float(auc_by_task[t][m2]) - 0.5 for t in tasks]
        r = _pearsonr(x, y)
        rho = _spearmanr(x, y)
        agree = sum(1 for a, b in zip(x, y) if _sign(a) == _sign(b))
        stab_rows.append(
            {
                "m1": int(m1),
                "m2": int(m2),
                "n": int(len(tasks)),
                "pearson_r": r,
                "spearman_rho": rho,
                "sign_agree": int(agree),
                "sign_rate": float(agree) / float(len(tasks)),
            }
        )
        # flips list
        for t, a, b in zip(tasks, x, y):
            if _sign(a) == 0 or _sign(b) == 0:
                continue
            if _sign(a) != _sign(b):
                flip_rows.append(
                    {
                        "m1": int(m1),
                        "m2": int(m2),
                        "comparison": t[0],
                        "metric": t[1],
                        "auc1": float(auc_by_task[t][m1]),
                        "auc2": float(auc_by_task[t][m2]),
                    }
                )

    # Summary line.
    m_in = ",".join(str(int(m)) for m in ms)
    m_use = ",".join(str(int(m)) for m in usable_ms)
    s = (
        "Cross-resolution stability of recoding discrimination AUC for uplift-window statistics "
        f"(tasks = comparison$\\times$metric; input $m\\in\\{{{m_in}\\}}$; usable $m\\in\\{{{m_use}\\}}$; $n={len(tasks)}$ tasks)."
    )
    write_text_atomic(out_summary, s + "\n")

    # LaTeX stability table.
    stab_rows.sort(key=lambda r: (int(r["m1"]), int(r["m2"])))
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r r r r r r}")
    lines.append("\\toprule")
    lines.append("$m_1$ & $m_2$ & $n$ & Pearson $r$ & Spearman $\\rho$ & sign-agree \\\\")
    lines.append("\\midrule")
    for r in stab_rows:
        lines.append(
            f"{int(r['m1'])} & {int(r['m2'])} & {int(r['n'])} & {_fmt_float(r['pearson_r'], nd=3)} & {_fmt_float(r['spearman_rho'], nd=3)} & "
            f"{int(r['sign_agree'])}/{int(r['n'])} ({_fmt_percent(100.0*float(r['sign_rate']), nd=1)}) \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")
    write_text_atomic(out_table, "\n".join(lines) + "\n")

    # LaTeX flips table.
    flip_rows.sort(key=lambda r: (int(r["m1"]), int(r["m2"]), str(r["comparison"]), str(r["metric"])))
    fl: list[str] = []
    fl.append("\\begingroup")
    fl.append("\\hbadness=10000")
    fl.append("\\small")
    fl.append("\\setlength{\\tabcolsep}{6pt}")
    fl.append("\\renewcommand{\\arraystretch}{1.15}")
    fl.append("\\setlength{\\LTleft}{0pt}")
    fl.append("\\setlength{\\LTright}{0pt}")
    fl.append("\\begin{longtable}{r r l l r r}")
    fl.append("\\toprule")
    fl.append("$m_1$ & $m_2$ & comparison & metric & AUC$_{m_1}$ & AUC$_{m_2}$ \\\\")
    fl.append("\\midrule")
    if flip_rows:
        for r in flip_rows:
            cmp_escaped = str(r["comparison"]).replace("_", "\\_")
            metric_escaped = str(r["metric"]).replace("_", "\\_")
            fl.append(
                f"{int(r['m1'])} & {int(r['m2'])} & {cmp_escaped} & {metric_escaped} & "
                f"{_fmt_float(r['auc1'], nd=4)} & {_fmt_float(r['auc2'], nd=4)} \\\\"
            )
    else:
        fl.append(f"\\multicolumn{{6}}{{l}}{{No sign flips across usable $m$.}} \\\\")
    fl.append("\\bottomrule")
    fl.append("\\end{longtable}")
    fl.append("\\endgroup")
    fl.append("")
    write_text_atomic(out_flips, "\n".join(fl) + "\n")

    write_json_atomic(cache_meta_path(out_table), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_table)
    print("Wrote:", out_flips)


if __name__ == "__main__":
    main()


