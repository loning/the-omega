# -*- coding: utf-8 -*-
"""
Incremental predictive power of uplift-window statistics (purely computational).

Reviewer-facing question:
  After controlling for obvious local factors (stop identity, +4 base) and
  window composition (GC + dinucleotide frequencies), do uplift-window features
  (u_before, u_after, u_after-u_before) add *independent* discriminative signal?

Task (fixed):
  Classify transl_except recoding sites (y=1) vs CDS-deduplicated terminal stops (y=0)
  using a nested feature family.

Models (nested, pre-registered):
  M0: stop identity + +4 base (categorical)  [+ intercept]
  M1: M0 + composition features (GC + 16-dinuc) for before/after windows
  M2: M1 + uplift-window statistics (u_before, u_after, u_after-u_before)

Evaluation:
  - group-aware 5-fold CV by CDS key (version, cds_location, translation_start)
  - AUC computed as Mann–Whitney concordance on predicted probabilities
  - permutation test (label shuffle) for ΔAUC = AUC(M2)-AUC(M1)

Outputs (sections/generated/):
  - incremental_predictive_power_summary.tex
  - incremental_predictive_power_table.tex
  - cache JSON under data/_cache/

This script uses numpy for logistic regression (Newton / IRLS) and speed.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic


SCRIPT_VERSION = 1

DINUC_ORDER = [a + b for a in "ACGT" for b in "ACGT"]
STOP_CODONS = ("UAA", "UAG", "UGA")
BASES_RNA = ("A", "C", "G", "U")


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def recoding_jsonl_default() -> Path:
    return data_root() / "recoding_genbank" / "recoding_sites.jsonl"


def _file_fingerprint(path: Path) -> dict[str, object]:
    st = path.stat()
    return {
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _is_num(x: object) -> bool:
    return isinstance(x, (int, float)) and (not isinstance(x, bool)) and math.isfinite(float(x))


def _dna_to_rna(s: str | None) -> str | None:
    if s is None:
        return None
    return str(s).upper().replace("T", "U")


def _one_hot(value: str, categories: list[str], *, drop: str | None = None) -> list[float]:
    out = []
    for c in categories:
        if drop is not None and c == drop:
            continue
        out.append(1.0 if value == c else 0.0)
    return out


def _dinuc_vec_16(freq: dict[str, float] | None) -> list[float] | None:
    if freq is None:
        return None
    return [float(freq.get(k, 0.0)) for k in DINUC_ORDER]


@dataclass(frozen=True)
class Sample:
    y: int  # 1=recoding, 0=terminal stop
    group: tuple[str, str, int]  # (version, cds_location, translation_start)
    stop_codon: str  # UAA/UAG/UGA (RNA)
    plus4: str  # A/C/G/U/N
    # composition features
    before_gc: float
    after_gc: float
    before_dinuc16: list[float]
    after_dinuc16: list[float]
    # uplift features
    u_before: float
    u_after: float

    @property
    def u_diff(self) -> float:
        return float(self.u_after) - float(self.u_before)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Incremental predictive power of uplift-window statistics (CV + permutation).")
    p.add_argument("--in-jsonl", default=str(recoding_jsonl_default()), help="Input recoding_sites.jsonl (with sequences/features).")
    p.add_argument("--analysis-version", type=int, default=7, help="Filter: analysis_version.")
    p.add_argument("--k", type=int, default=10, help="Filter: window radius k.")
    p.add_argument("--folds", type=int, default=5, help="Group-aware CV folds.")
    p.add_argument("--l2", type=float, default=1.0, help="L2 regularization strength (lambda).")
    p.add_argument("--max-iter", type=int, default=25, help="Max Newton iterations for logistic regression.")
    p.add_argument("--n-perm", type=int, default=200, help="Permutation count for ΔAUC(M2-M1) (0 disables).")
    p.add_argument("--seed", type=int, default=0, help="RNG seed.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # stable sigmoid
    out = np.empty_like(z, dtype=np.float64)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _fit_logreg_newton(
    X: np.ndarray,
    y: np.ndarray,
    *,
    l2: float,
    max_iter: int,
    tol: float = 1e-8,
) -> np.ndarray:
    """
    L2-regularized logistic regression via Newton iterations.
    Intercept is assumed to be the first column and is NOT regularized.
    """
    n, d = X.shape
    w = np.zeros(d, dtype=np.float64)
    reg = np.full(d, float(l2), dtype=np.float64)
    reg[0] = 0.0  # no penalty on intercept

    for _ in range(int(max_iter)):
        z = X @ w
        p = _sigmoid(z)
        # gradient
        g = X.T @ (p - y) + reg * w
        # Hessian: X^T W X + diag(reg)
        W = p * (1.0 - p)
        # Avoid forming full diag(W); weight rows instead.
        Xw = X * W[:, None]
        H = X.T @ Xw
        H[np.diag_indices_from(H)] += reg
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            # Fall back to pseudo-inverse step (rare, but keep the script robust).
            step = np.linalg.pinv(H) @ g
        w_new = w - step
        if float(np.max(np.abs(w_new - w))) < float(tol):
            w = w_new
            break
        w = w_new
    return w


def _auc_mann_whitney(scores: np.ndarray, y: np.ndarray) -> float:
    """
    AUC as Mann–Whitney concordance probability (with average ranks for ties).
    y must be 0/1.
    """
    y = y.astype(np.int8)
    pos = scores[y == 1]
    neg = scores[y == 0]
    n1 = int(pos.size)
    n0 = int(neg.size)
    if n1 <= 0 or n0 <= 0:
        return float("nan")
    all_vals = np.concatenate([pos, neg]).tolist()
    order = sorted(range(len(all_vals)), key=lambda i: all_vals[i])
    ranks = [0.0] * len(all_vals)
    i = 0
    r = 1
    while i < len(all_vals):
        j = i
        v = all_vals[order[i]]
        while j < len(all_vals) and all_vals[order[j]] == v:
            j += 1
        avg = 0.5 * (r + (r + (j - i) - 1))
        for k in range(i, j):
            ranks[order[k]] = float(avg)
        r += (j - i)
        i = j
    r_pos = float(sum(ranks[:n1]))
    u = r_pos - (n1 * (n1 + 1)) / 2.0
    auc = float(u) / float(n1 * n0)
    return min(1.0, max(0.0, auc))


def _make_group_folds(groups: list[tuple[str, str, int]], *, n_folds: int, seed: int) -> dict[tuple[str, str, int], int]:
    """
    Deterministic group->fold assignment: sort by stable hash, then round-robin.
    """
    def h(g: tuple[str, str, int]) -> str:
        s = f"{g[0]}|{g[1]}|{g[2]}|{seed}"
        return hashlib_sha256_hex(s)[:16]

    gs = sorted(set(groups), key=h)
    out: dict[tuple[str, str, int], int] = {}
    for i, g in enumerate(gs):
        out[g] = int(i % int(n_folds))
    return out


def hashlib_sha256_hex(s: str) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def _build_samples(in_jsonl: Path, *, analysis_version: int, k: int) -> list[Sample]:
    """
    Build samples with complete features for M2 (strict intersection).
    Terminal stops are CDS-deduplicated by (version, cds_location, translation_start).
    """
    # First pass: collect recoding positives and terminal-stop candidates.
    rec: list[Sample] = []
    term_by_cds: dict[tuple[str, str, int], dict[str, Any]] = {}

    with in_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if not isinstance(r, dict):
                continue
            if int(r.get("analysis_version") or 0) != int(analysis_version):
                continue
            if int(r.get("k") or 0) != int(k):
                continue

            version = str(r.get("version") or "").strip()
            cds_location = str(r.get("cds_location") or "").strip()
            ts = r.get("translation_start")
            if (not version) or (not cds_location) or (not isinstance(ts, int)):
                continue
            group = (version, cds_location, int(ts))

            # ---- Positive sample (recoding site) ----
            stop_codon = str(r.get("codon_rna") or "").strip().upper()
            if stop_codon not in STOP_CODONS:
                continue
            plus4 = str(r.get("plus4_nt") or "").strip().upper()
            if plus4 not in BASES_RNA:
                plus4 = "N"
            before_gc = r.get("before_gc")
            after_gc = r.get("after_gc")
            bd = _dinuc_vec_16(r.get("before_dinuc"))
            ad = _dinuc_vec_16(r.get("after_dinuc"))
            ub = r.get("before_mean_delta")
            ua = r.get("after_mean_delta")
            # Require complete features for M2.
            if not (_is_num(before_gc) and _is_num(after_gc) and _is_num(ub) and _is_num(ua)):
                continue
            if bd is None or ad is None:
                continue
            rec.append(
                Sample(
                    y=1,
                    group=group,
                    stop_codon=stop_codon,
                    plus4=plus4,
                    before_gc=float(before_gc),
                    after_gc=float(after_gc),
                    before_dinuc16=[float(x) for x in bd],
                    after_dinuc16=[float(x) for x in ad],
                    u_before=float(ub),
                    u_after=float(ua),
                )
            )

            # ---- Terminal-stop candidate for this CDS (deduplicated downstream) ----
            # Keep the last-seen record for that CDS; fields are CDS-level in exp_recoding_sites.
            term_by_cds[group] = r

    # Build terminal-stop negatives from the CDS map.
    term: list[Sample] = []
    for group, r in term_by_cds.items():
        stop_codon = str(r.get("terminal_stop") or "").strip().upper()
        if stop_codon not in STOP_CODONS:
            continue
        # +4 base for terminal stop: from terminal_after_seq_dna if available
        plus4 = "N"
        ta = _dna_to_rna(r.get("terminal_after_seq_dna"))
        if isinstance(ta, str) and len(ta) >= 1:
            plus4 = ta[0]
        if plus4 not in BASES_RNA:
            plus4 = "N"

        before_gc = r.get("terminal_before_gc")
        after_gc = r.get("terminal_after_gc")
        bd = _dinuc_vec_16(r.get("terminal_before_dinuc"))
        ad = _dinuc_vec_16(r.get("terminal_after_dinuc"))
        ub = r.get("terminal_before_mean_delta")
        ua = r.get("terminal_after_mean_delta")
        if not (_is_num(before_gc) and _is_num(after_gc) and _is_num(ub) and _is_num(ua)):
            continue
        if bd is None or ad is None:
            continue
        term.append(
            Sample(
                y=0,
                group=group,
                stop_codon=stop_codon,
                plus4=plus4,
                before_gc=float(before_gc),
                after_gc=float(after_gc),
                before_dinuc16=[float(x) for x in bd],
                after_dinuc16=[float(x) for x in ad],
                u_before=float(ub),
                u_after=float(ua),
            )
        )

    return rec + term


def _design_matrix(samples: list[Sample], *, model: str) -> tuple[np.ndarray, np.ndarray, list[tuple[str, str, int]]]:
    """
    Return (X, y, groups) for model in {"M0","M1","M2"}.
    """
    if model not in ("M0", "M1", "M2"):
        raise ValueError("model must be M0/M1/M2")

    stop_cats = list(STOP_CODONS)  # UAA/UAG/UGA
    plus4_cats = list(BASES_RNA) + ["N"]

    X_rows: list[list[float]] = []
    ys: list[int] = []
    groups: list[tuple[str, str, int]] = []

    for s in samples:
        row: list[float] = []
        # intercept
        row.append(1.0)
        # stop identity (drop UAA as reference)
        row += _one_hot(s.stop_codon, stop_cats, drop="UAA")
        # +4 base (drop A as reference)
        row += _one_hot(s.plus4, plus4_cats, drop="A")

        if model in ("M1", "M2"):
            # Composition: GC + dinuc for before/after
            row.append(float(s.before_gc))
            row.append(float(s.after_gc))
            row += [float(x) for x in s.before_dinuc16]
            row += [float(x) for x in s.after_dinuc16]

        if model == "M2":
            row.append(float(s.u_before))
            row.append(float(s.u_after))
            row.append(float(s.u_diff))

        X_rows.append(row)
        ys.append(int(s.y))
        groups.append(tuple(s.group))

    X = np.array(X_rows, dtype=np.float64)
    y = np.array(ys, dtype=np.float64)
    return X, y, groups


def _standardize_inplace(X_train: np.ndarray, X_test: np.ndarray, *, cols: list[int]) -> None:
    """
    Standardize selected columns in-place using train mean/std.
    """
    for j in cols:
        m = float(np.mean(X_train[:, j]))
        s = float(np.std(X_train[:, j], ddof=0))
        if s <= 0:
            s = 1.0
        X_train[:, j] = (X_train[:, j] - m) / s
        X_test[:, j] = (X_test[:, j] - m) / s


def _cv_auc(
    X: np.ndarray,
    y: np.ndarray,
    groups: list[tuple[str, str, int]],
    *,
    n_folds: int,
    seed: int,
    l2: float,
    max_iter: int,
    standardize_cols: list[int],
) -> tuple[float, list[float]]:
    """
    Group-aware CV AUC. Returns (mean_auc, per_fold_aucs).
    """
    fold_map = _make_group_folds(groups, n_folds=int(n_folds), seed=int(seed))
    aucs: list[float] = []
    for fold in range(int(n_folds)):
        test_mask = np.array([fold_map[g] == fold for g in groups], dtype=bool)
        train_mask = ~test_mask
        if int(np.sum(test_mask)) <= 0:
            continue
        Xtr = X[train_mask].copy()
        Xte = X[test_mask].copy()
        ytr = y[train_mask].copy()
        yte = y[test_mask].copy()

        # Standardize numeric columns (no-op if list empty).
        _standardize_inplace(Xtr, Xte, cols=standardize_cols)

        w = _fit_logreg_newton(Xtr, ytr, l2=float(l2), max_iter=int(max_iter))
        p = _sigmoid(Xte @ w)
        auc = _auc_mann_whitney(p, yte.astype(np.int8))
        aucs.append(float(auc))
    mean_auc = float(sum(aucs) / float(len(aucs))) if aucs else float("nan")
    return mean_auc, aucs


def main() -> None:
    args = parse_args()
    in_jsonl = Path(args.in_jsonl)
    if not in_jsonl.exists():
        raise SystemExit(f"Input not found: {in_jsonl}")

    out_sum = generated_dir() / "incremental_predictive_power_summary.tex"
    out_tbl = generated_dir() / "incremental_predictive_power_table.tex"
    cache_file = data_root() / "_cache" / f"incremental_predictive_power_v{int(SCRIPT_VERSION)}.json"

    cache_key = {
        "analysis": "incremental_predictive_power",
        "version": int(SCRIPT_VERSION),
        "analysis_version": int(args.analysis_version),
        "k": int(args.k),
        "folds": int(args.folds),
        "l2": float(args.l2),
        "max_iter": int(args.max_iter),
        "n_perm": int(args.n_perm),
        "seed": int(args.seed),
        "in_jsonl": _file_fingerprint(in_jsonl),
        "out": [str(out_sum), str(out_tbl)],
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and out_sum.exists() and out_tbl.exists() and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {cache_file}")
        return

    # Build samples with complete features for M2.
    samples = _build_samples(in_jsonl, analysis_version=int(args.analysis_version), k=int(args.k))
    if not samples:
        raise SystemExit("No samples after filtering. Check input JSONL and filters.")
    n_pos = sum(1 for s in samples if s.y == 1)
    n_neg = sum(1 for s in samples if s.y == 0)
    n_groups = len(set(s.group for s in samples))

    # Design matrices.
    X0, y0, g0 = _design_matrix(samples, model="M0")
    X1, y1, g1 = _design_matrix(samples, model="M1")
    X2, y2, g2 = _design_matrix(samples, model="M2")
    if not (np.allclose(y0, y1) and np.allclose(y1, y2)):
        raise AssertionError("y mismatch across models")
    if not (g0 == g1 == g2):
        raise AssertionError("group mismatch across models")

    # Standardize columns (by index) for M1/M2 numeric features.
    # Layout:
    #   [0] intercept
    #   stop one-hot (2 cols) + plus4 one-hot (4 cols) -> 6 cols total after intercept
    # M1 adds: before_gc, after_gc (2) + before_dinuc16 (16) + after_dinuc16 (16) -> 34 numeric
    # M2 adds: u_before, u_after, u_diff (3) -> numeric too
    base_cat_cols = 1 + 2 + 4  # intercept + (stop,UAA dropped)2 + (+4,A dropped)4
    # numeric start index for M1:
    m1_num_start = base_cat_cols
    m1_num_cols = list(range(m1_num_start, m1_num_start + 34))
    # M2 numeric includes M1 numeric + 3 uplift stats
    m2_num_cols = list(m1_num_cols) + list(range(m1_num_start + 34, m1_num_start + 34 + 3))

    # CV AUCs.
    mean0, aucs0 = _cv_auc(X0, y0, g0, n_folds=int(args.folds), seed=int(args.seed), l2=float(args.l2), max_iter=int(args.max_iter), standardize_cols=[])
    mean1, aucs1 = _cv_auc(X1, y1, g1, n_folds=int(args.folds), seed=int(args.seed), l2=float(args.l2), max_iter=int(args.max_iter), standardize_cols=m1_num_cols)
    mean2, aucs2 = _cv_auc(X2, y2, g2, n_folds=int(args.folds), seed=int(args.seed), l2=float(args.l2), max_iter=int(args.max_iter), standardize_cols=m2_num_cols)

    d10 = float(mean1 - mean0)
    d21 = float(mean2 - mean1)

    # Permutation test for ΔAUC(M2-M1)
    n_perm = int(args.n_perm)
    p_perm = None
    if n_perm > 0:
        rng = random.Random(int(args.seed))
        deltas: list[float] = []
        # Keep group folds fixed; shuffle labels globally (event-level) under the null.
        y_list = y0.astype(np.int8).tolist()
        for t in range(n_perm):
            y_perm = list(y_list)
            rng.shuffle(y_perm)
            y_perm_arr = np.array(y_perm, dtype=np.float64)
            m1p, _ = _cv_auc(X1, y_perm_arr, g1, n_folds=int(args.folds), seed=int(args.seed), l2=float(args.l2), max_iter=int(args.max_iter), standardize_cols=m1_num_cols)
            m2p, _ = _cv_auc(X2, y_perm_arr, g2, n_folds=int(args.folds), seed=int(args.seed), l2=float(args.l2), max_iter=int(args.max_iter), standardize_cols=m2_num_cols)
            deltas.append(float(m2p - m1p))
        ge = sum(1 for x in deltas if x >= d21)
        p_perm = (ge + 1) / float(n_perm + 1)

    # Write LaTeX table.
    tbl: list[str] = []
    tbl.append("\\begin{center}")
    tbl.append("\\small")
    tbl.append("\\setlength{\\tabcolsep}{6pt}")
    tbl.append("\\renewcommand{\\arraystretch}{1.15}")
    tbl.append("\\begin{tabular}{lrr}")
    tbl.append("\\toprule")
    tbl.append("model & mean AUC (CV) & notes \\\\")
    tbl.append("\\midrule")
    tbl.append(f"M0 & {mean0:.4f} & stop identity + +4 base \\\\")
    tbl.append(f"M1 & {mean1:.4f} & M0 + GC + dinucleotide (before/after) \\\\")
    tbl.append(f"M2 & {mean2:.4f} & M1 + uplift windows $\\overline{{U}}_{{\\mathrm{{before}}}},\\overline{{U}}_{{\\mathrm{{after}}}},\\Delta$ \\\\")
    tbl.append("\\bottomrule")
    tbl.append("\\end{tabular}")
    tbl.append("\\end{center}")
    tbl.append("")
    write_text_atomic(out_tbl, "\n".join(tbl) + "\n")

    # Write LaTeX summary paragraph.
    s_lines: list[str] = []
    s_lines.append(
        f"Incremental predictive power (GenBank \\texttt{{transl\\_except}}; $k={int(args.k)}$; "
        f"group-aware {int(args.folds)}-fold CV by CDS; $n_1={n_pos}$ recoding events, $n_0={n_neg}$ terminal-stop events; groups={n_groups}). "
        f"AUC: M0={mean0:.4f}, M1={mean1:.4f}, M2={mean2:.4f}. "
        f"Improvements: $\\Delta\\mathrm{{AUC}}_{{1-0}}={d10:+.4f}$, $\\Delta\\mathrm{{AUC}}_{{2-1}}={d21:+.4f}$."
    )
    if p_perm is not None:
        s_lines.append(f"Permutation test for $\\Delta\\mathrm{{AUC}}_{{2-1}}>0$: $p={float(p_perm):.4f}$ (n={n_perm}).")
    write_text_atomic(out_sum, " ".join(s_lines).strip() + "\n")

    # Cache JSON.
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        cache_file,
        {
            "ok": True,
            "script_version": int(SCRIPT_VERSION),
            "analysis_version": int(args.analysis_version),
            "k": int(args.k),
            "folds": int(args.folds),
            "l2": float(args.l2),
            "max_iter": int(args.max_iter),
            "n_perm": int(args.n_perm),
            "seed": int(args.seed),
            "n_pos": int(n_pos),
            "n_neg": int(n_neg),
            "n_groups": int(n_groups),
            "auc": {"M0": float(mean0), "M1": float(mean1), "M2": float(mean2)},
            "delta_auc": {"M1-M0": float(d10), "M2-M1": float(d21)},
            "p_perm_M2-M1": float(p_perm) if p_perm is not None else None,
            "fold_aucs": {"M0": aucs0, "M1": aucs1, "M2": aucs2},
        },
    )
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote:", out_sum)
    print("Wrote:", out_tbl)


if __name__ == "__main__":
    main()

