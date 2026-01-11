# -*- coding: utf-8 -*-
"""
RNA secondary structure vs Uplift correlation analysis.

Tests whether uplift U correlates with RNA structure features and whether
this correlation persists after controlling for GC and dinucleotide composition.

Output:
  - sections/generated/uplift_rna_structure_correlation_summary.tex
  - sections/generated/uplift_rna_structure_correlation_table.tex
"""

from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import fold_codon

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
NUCS = "ACGU"
DINUCS = [a + b for a in NUCS for b in NUCS]

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data"
def cache_dir():
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

def gc_fraction(seq: str) -> float:
    seq = seq.upper().replace("T", "U")
    if not seq: return float("nan")
    return sum(1 for ch in seq if ch in "GC") / len(seq)

def dinuc_freq(seq: str) -> np.ndarray:
    seq = seq.upper().replace("T", "U")
    dinuc_idx = {d: i for i, d in enumerate(DINUCS)}
    counts = np.zeros(16, dtype=float)
    for i in range(len(seq) - 1):
        d = seq[i:i+2]
        if d[0] in NUCS and d[1] in NUCS:
            counts[dinuc_idx[d]] += 1.0
    if counts.sum() > 0: counts /= counts.sum()
    return counts

def gc_structure_proxy(seq: str) -> float:
    gc = gc_fraction(seq)
    return -0.5 * len(seq) * (gc - 0.3) if not np.isnan(gc) else float("nan")

def seq_to_codons(seq: str) -> list[str]:
    s = seq.upper().replace("T", "U")
    return [s[i:i+3] for i in range(0, len(s)-2, 3) if len(s[i:i+3]) == 3]

def window_mean_uplift(seq: str) -> float:
    codons = seq_to_codons(seq)
    uplifts = []
    for c in codons:
        try:
            cf = fold_codon(c, MU_STAR)
            uplifts.append(float(cf.delta))
        except: pass
    return float(np.mean(uplifts)) if uplifts else float("nan")

@dataclass
class WindowRecord:
    stop_codon: str
    u_before: float; u_after: float
    gc_before: float; gc_after: float
    dinuc_before: np.ndarray; dinuc_after: np.ndarray
    mfe_before: float; mfe_after: float

def load_refseq_windows(shards_dir, k, n_per_stop, seed):
    rng = np.random.default_rng(seed)
    shard_files = sorted(shards_dir.glob("*.json"))
    if not shard_files: raise FileNotFoundError(f"No shards in {shards_dir}")
    
    all_recs = {"UAA": [], "UAG": [], "UGA": []}
    for sf in shard_files:
        with open(sf) as f: data = json.load(f)
        for item in data.get("items", []):
            stop = item.get("stop_codon")
            if stop not in all_recs: continue
            sc = item.get("stop_context", {}).get(str(k), {})
            bseq, aseq = sc.get("before_seq", ""), sc.get("after_seq", "")
            if len(bseq) < 3*k or len(aseq) < 3*k: continue
            ub = float(sc.get("u_before", float("nan")))
            ua = float(sc.get("u_after", float("nan")))
            if np.isnan(ub) or np.isnan(ua): continue
            all_recs[stop].append({"bseq": bseq, "aseq": aseq, "ub": ub, "ua": ua})
    
    result = {}
    for stop, recs in all_recs.items():
        if len(recs) > n_per_stop:
            idx = rng.choice(len(recs), size=n_per_stop, replace=False)
            recs = [recs[i] for i in idx]
        records = []
        for r in recs:
            records.append(WindowRecord(
                stop_codon=stop, u_before=r["ub"], u_after=r["ua"],
                gc_before=gc_fraction(r["bseq"]), gc_after=gc_fraction(r["aseq"]),
                dinuc_before=dinuc_freq(r["bseq"]), dinuc_after=dinuc_freq(r["aseq"]),
                mfe_before=gc_structure_proxy(r["bseq"]), mfe_after=gc_structure_proxy(r["aseq"]),
            ))
        result[stop] = records
    return result

def spearman_corr(x, y):
    from scipy.stats import spearmanr
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 10: return float("nan"), float("nan")
    r, p = spearmanr(x[mask], y[mask])
    return float(r), float(p)

def partial_corr(u, mfe, gc, dinuc):
    from scipy.stats import spearmanr
    mask = ~(np.isnan(u) | np.isnan(mfe) | np.isnan(gc))
    if mask.sum() < 30: return float("nan"), float("nan")
    X = np.column_stack([gc[mask], dinuc[mask]])
    from numpy.linalg import lstsq
    cu, _, _, _ = lstsq(X, u[mask], rcond=None)
    cm, _, _, _ = lstsq(X, mfe[mask], rcond=None)
    r, p = spearmanr(u[mask] - X @ cu, mfe[mask] - X @ cm)
    return float(r), float(p)

def run_analysis(records):
    results = {}
    all_ub, all_ua, all_mb, all_ma = [], [], [], []
    all_gb, all_ga, all_db, all_da = [], [], [], []
    
    for stop, recs in records.items():
        ub = np.array([r.u_before for r in recs])
        ua = np.array([r.u_after for r in recs])
        mb = np.array([r.mfe_before for r in recs])
        ma = np.array([r.mfe_after for r in recs])
        gb = np.array([r.gc_before for r in recs])
        ga = np.array([r.gc_after for r in recs])
        db = np.array([r.dinuc_before for r in recs])
        da = np.array([r.dinuc_after for r in recs])
        
        all_ub.extend(ub); all_ua.extend(ua)
        all_mb.extend(mb); all_ma.extend(ma)
        all_gb.extend(gb); all_ga.extend(ga)
        all_db.extend(db); all_da.extend(da)
        
        rb, pb = spearman_corr(ub, mb)
        ra, pa = spearman_corr(ua, ma)
        rpb, ppb = partial_corr(ub, mb, gb, db)
        rpa, ppa = partial_corr(ua, ma, ga, da)
        
        results[stop] = {
            "n": len(recs),
            "before": {"raw": {"r": rb, "p": pb}, "partial": {"r": rpb, "p": ppb}},
            "after": {"raw": {"r": ra, "p": pa}, "partial": {"r": rpa, "p": ppa}},
        }
    
    ub, ua = np.array(all_ub), np.array(all_ua)
    mb, ma = np.array(all_mb), np.array(all_ma)
    gb, ga = np.array(all_gb), np.array(all_ga)
    db, da = np.array(all_db), np.array(all_da)
    
    rb, pb = spearman_corr(ub, mb)
    ra, pa = spearman_corr(ua, ma)
    rpb, ppb = partial_corr(ub, mb, gb, db)
    rpa, ppa = partial_corr(ua, ma, ga, da)
    
    results["pooled"] = {
        "n": len(ub),
        "before": {"raw": {"r": rb, "p": pb}, "partial": {"r": rpb, "p": ppb}},
        "after": {"raw": {"r": ra, "p": pa}, "partial": {"r": rpa, "p": ppa}},
    }
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n-per-stop", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    out_sum = generated_dir() / "uplift_rna_structure_correlation_summary.tex"
    out_tbl = generated_dir() / "uplift_rna_structure_correlation_table.tex"
    cache = cache_dir() / f"uplift_rna_structure_v{ANALYSIS_VERSION}.json"
    meta = {"v": ANALYSIS_VERSION, "k": args.k, "n": args.n_per_stop}
    
    if not args.force and cache.exists():
        try:
            with open(cache) as f: cached = json.load(f)
            if cached.get("k") == args.k and cached.get("n_per_stop") == args.n_per_stop:
                print(f"[cache] {cache}"); _emit(cached, out_sum, out_tbl, meta); return
        except: pass
    
    shards = data_dir() / "refseq_hsapiens_mrna" / "shards" / f"k{args.k}_v4"
    for v in [3,2,1]:
        if not shards.exists():
            shards = data_dir() / "refseq_hsapiens_mrna" / "shards" / f"k{args.k}_v{v}"
    if not shards.exists():
        print(f"[error] No shards at {shards}", file=sys.stderr); sys.exit(1)
    
    print(f"[load] {shards}"); records = load_refseq_windows(shards, args.k, args.n_per_stop, args.seed)
    for s, r in records.items(): print(f"  {s}: {len(r)}")
    
    print("[analyze]"); results = run_analysis(records)
    results["k"] = args.k; results["n_per_stop"] = args.n_per_stop
    write_json_atomic(cache, results)
    _emit(results, out_sum, out_tbl, meta)

def _emit(res, out_sum, out_tbl, meta):
    k = res.get("k", 10)
    p = res.get("pooled", {})
    bb = p.get("before", {}).get("raw", {})
    bp = p.get("before", {}).get("partial", {})
    ab = p.get("after", {}).get("raw", {})
    ap_ = p.get("after", {}).get("partial", {})
    
    txt = (f"RNA structure (GC-proxy) vs Uplift ($k={k}$, n={p.get('n',0)}). "
           f"Before: raw $\\rho={bb.get('r',0):.3f}$ ($p={bb.get('p',1):.4f}$), "
           f"partial $\\rho={bp.get('r',0):.3f}$ ($p={bp.get('p',1):.4f}$). "
           f"After: raw $\\rho={ab.get('r',0):.3f}$ ($p={ab.get('p',1):.4f}$), "
           f"partial $\\rho={ap_.get('r',0):.3f}$ ($p={ap_.get('p',1):.4f}$).\n")
    write_text_atomic(out_sum, txt); write_json_atomic(cache_meta_path(out_sum), meta)
    print(f"Wrote: {out_sum}")
    
    def f(x): return f"{x:.3f}" if x and not np.isnan(x) else "--"
    rows = ["\\begin{center}\\small\\begin{tabular}{lcccc}\\toprule",
            "Stop & raw$_b$ & partial$_b$ & raw$_a$ & partial$_a$ \\\\\\midrule"]
    for s in ["UAA","UAG","UGA","pooled"]:
        r = res.get(s, {})
        bb = r.get("before",{}).get("raw",{}); bp = r.get("before",{}).get("partial",{})
        ab = r.get("after",{}).get("raw",{}); ap_ = r.get("after",{}).get("partial",{})
        lbl = s if s != "pooled" else "\\textbf{Pooled}"
        rows.append(f"{lbl} & {f(bb.get('r'))} & {f(bp.get('r'))} & {f(ab.get('r'))} & {f(ap_.get('r'))} \\\\")
    rows.append("\\bottomrule\\end{tabular}\\end{center}")
    write_text_atomic(out_tbl, "\n".join(rows)+"\n"); write_json_atomic(cache_meta_path(out_tbl), meta)
    print(f"Wrote: {out_tbl}")

if __name__ == "__main__": main()
