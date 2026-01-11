# -*- coding: utf-8 -*-
"""
Stop-context window analysis: Dinucleotide shuffle null + Structure correlation.

Extracts per-window sequences from RefSeq FASTA files, then runs:
1. Dinucleotide shuffle null (per-window Eulerian-trail permutation)
2. Uplift vs GC-proxy structure correlation (raw + partial)

Output:
  - sections/generated/stop_context_window_dinuc_null.tex
  - sections/generated/stop_context_window_structure_corr.tex
"""

from __future__ import annotations
import argparse, gzip, json, math, sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, iter_fasta, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}
NUCS = "ACGU"
DINUCS = [a + b for a in NUCS for b in NUCS]

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data" / "refseq_hsapiens_mrna"
def cache_dir():
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

# ---- Sequence utilities ----

def normalize_seq(seq: str) -> str:
    return seq.upper().replace("T", "U")

def gc_fraction(seq: str) -> float:
    seq = normalize_seq(seq)
    if not seq: return float("nan")
    return sum(1 for ch in seq if ch in "GC") / len(seq)

def dinuc_freq(seq: str) -> np.ndarray:
    seq = normalize_seq(seq)
    dinuc_idx = {d: i for i, d in enumerate(DINUCS)}
    counts = np.zeros(16, dtype=float)
    for i in range(len(seq) - 1):
        d = seq[i:i+2]
        if d[0] in NUCS and d[1] in NUCS:
            counts[dinuc_idx[d]] += 1.0
    if counts.sum() > 0: counts /= counts.sum()
    return counts

def gc_structure_proxy(seq: str) -> float:
    """GC-based proxy for RNA structure stability (higher GC = more stable)."""
    gc = gc_fraction(seq)
    return -0.5 * len(seq) * (gc - 0.3) if not np.isnan(gc) else float("nan")

def window_mean_uplift(seq: str) -> float:
    """Compute mean uplift for a codon window sequence."""
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    uplifts = []
    for c in codons:
        if c in GENETIC_CODE:
            try:
                cf = fold_codon(c, MU_STAR)
                uplifts.append(float(cf.delta))
            except: pass
    return float(np.mean(uplifts)) if uplifts else float("nan")

# ---- Dinucleotide shuffle (Eulerian trail) ----

def dinuc_shuffle(seq: str, rng: np.random.Generator) -> str:
    s = normalize_seq(seq)
    if len(s) <= 2: return s
    edges = {b: [] for b in NUCS}
    for i in range(len(s) - 1):
        a, b = s[i], s[i+1]
        if a in NUCS and b in NUCS:
            edges[a].append(b)
    for a in NUCS:
        rng.shuffle(edges[a])
    start = s[0] if s[0] in NUCS else "A"
    stack = [start]
    path = []
    while stack:
        v = stack[-1]
        if edges.get(v):
            stack.append(edges[v].pop())
        else:
            path.append(stack.pop())
    return "".join(reversed(path))[:len(s)]

# ---- ORF finding ----

@dataclass
class ORFInfo:
    start_base: int
    stop_base: int
    stop_codon: str
    length_codons: int

def best_orf(seq: str) -> ORFInfo | None:
    """Find best ORF (longest) across all 3 reading frames."""
    seq = normalize_seq(seq)
    best = None
    for frame in range(3):
        orfs = find_orfs(seq, frame=frame, min_codons=10)
        for (s, e) in orfs:
            length = (e - s) // 3
            stop_base = s + length * 3
            if stop_base + 3 > len(seq):
                continue
            stop_codon = seq[stop_base:stop_base+3]
            if stop_codon not in STOP_CODONS:
                continue
            if best is None or length > best.length_codons:
                best = ORFInfo(start_base=s, stop_base=stop_base, stop_codon=stop_codon, length_codons=length)
    return best

# ---- Window record ----

@dataclass
class WindowRecord:
    stop_codon: str
    before_seq: str
    after_seq: str
    u_before: float
    u_after: float
    gc_before: float
    gc_after: float
    dinuc_before: np.ndarray
    dinuc_after: np.ndarray
    mfe_before: float
    mfe_after: float

# ---- Data loading ----

def load_windows_from_fasta(fasta_files: list[Path], k: int, n_per_stop: int, seed: int) -> dict[str, list[WindowRecord]]:
    """Extract stop-context windows from FASTA files."""
    rng = np.random.default_rng(seed)
    
    all_records: dict[str, list[WindowRecord]] = {"UAA": [], "UAG": [], "UGA": []}
    n_scanned = 0
    n_with_orf = 0
    
    for fasta_path in fasta_files:
        opener = gzip.open if str(fasta_path).endswith(".gz") else open
        try:
            with opener(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta_handle(f):
                    n_scanned += 1
                    if n_scanned % 5000 == 0:
                        print(f"  scanned {n_scanned}, with_orf {n_with_orf}", flush=True)
                    
                    orf = best_orf(seq)
                    if orf is None:
                        continue
                    n_with_orf += 1
                    
                    stop = orf.stop_codon
                    stop_base = orf.stop_base
                    start_base = orf.start_base
                    
                    # Extract window sequences
                    before_start = stop_base - 3 * k
                    after_start = stop_base + 3
                    
                    if before_start < start_base:
                        continue
                    if after_start + 3 * k > len(seq):
                        continue
                    
                    before_seq = seq[before_start:stop_base]
                    after_seq = seq[after_start:after_start + 3 * k]
                    
                    if len(before_seq) != 3 * k or len(after_seq) != 3 * k:
                        continue
                    
                    u_before = window_mean_uplift(before_seq)
                    u_after = window_mean_uplift(after_seq)
                    
                    if np.isnan(u_before) or np.isnan(u_after):
                        continue
                    
                    rec = WindowRecord(
                        stop_codon=stop,
                        before_seq=before_seq,
                        after_seq=after_seq,
                        u_before=u_before,
                        u_after=u_after,
                        gc_before=gc_fraction(before_seq),
                        gc_after=gc_fraction(after_seq),
                        dinuc_before=dinuc_freq(before_seq),
                        dinuc_after=dinuc_freq(after_seq),
                        mfe_before=gc_structure_proxy(before_seq),
                        mfe_after=gc_structure_proxy(after_seq),
                    )
                    all_records[stop].append(rec)
        except Exception as e:
            print(f"  [warning] Error reading {fasta_path}: {e}", flush=True)
            continue
    
    print(f"  Total scanned: {n_scanned}, with ORF: {n_with_orf}", flush=True)
    
    # Sample n_per_stop from each
    result = {}
    for stop, recs in all_records.items():
        if len(recs) > n_per_stop:
            idx = rng.choice(len(recs), size=n_per_stop, replace=False)
            result[stop] = [recs[i] for i in idx]
        else:
            result[stop] = recs
        print(f"  {stop}: {len(result[stop])} windows", flush=True)
    
    return result

def _iter_fasta_handle(handle) -> Iterator[tuple[str, str]]:
    """Iterate over FASTA records from a file handle."""
    header = None
    seq_parts = []
    for line in handle:
        line = line.strip()
        if line.startswith(">"):
            if header is not None:
                yield header, "".join(seq_parts)
            header = line[1:].split()[0]
            seq_parts = []
        else:
            seq_parts.append(line)
    if header is not None:
        yield header, "".join(seq_parts)

# ---- Dinucleotide null analysis ----

def run_dinuc_null(records: dict[str, list[WindowRecord]], n_perm: int, seed: int, window: str) -> dict:
    """Run dinucleotide shuffle null for stop-class differences."""
    rng = np.random.default_rng(seed)
    results = {}
    
    for stop, recs in records.items():
        if not recs:
            continue
        
        if window == "before":
            seqs = [r.before_seq for r in recs]
            obs_values = [r.u_before for r in recs]
        else:
            seqs = [r.after_seq for r in recs]
            obs_values = [r.u_after for r in recs]
        
        obs_mean = float(np.mean(obs_values))
        
        # Null distribution
        null_means = []
        for _ in range(n_perm):
            perm_values = []
            for seq in seqs:
                shuffled = dinuc_shuffle(seq, rng)
                u = window_mean_uplift(shuffled)
                if not np.isnan(u):
                    perm_values.append(u)
            if perm_values:
                null_means.append(float(np.mean(perm_values)))
        
        results[stop] = {
            "n": len(recs),
            "obs_mean": obs_mean,
            "null_mean": float(np.mean(null_means)) if null_means else float("nan"),
            "null_std": float(np.std(null_means)) if null_means else float("nan"),
            "null_values": null_means,
        }
    
    # Pairwise contrasts
    pairs = [("UAG", "UAA"), ("UGA", "UAA"), ("UGA", "UAG")]
    contrasts = []
    for s1, s2 in pairs:
        if s1 not in results or s2 not in results:
            continue
        r1, r2 = results[s1], results[s2]
        obs_diff = r1["obs_mean"] - r2["obs_mean"]
        null1 = r1.get("null_values", [])
        null2 = r2.get("null_values", [])
        if null1 and null2:
            min_len = min(len(null1), len(null2))
            null_diffs = [null1[i] - null2[i] for i in range(min_len)]
            null_diff_mean = float(np.mean(null_diffs))
            null_diff_std = float(np.std(null_diffs))
            n_ge = sum(1 for d in null_diffs if d >= obs_diff)
            n_le = sum(1 for d in null_diffs if d <= obs_diff)
            p = 2 * min(n_ge, n_le) / len(null_diffs) if null_diffs else 1.0
        else:
            null_diff_mean = null_diff_std = p = float("nan")
        contrasts.append({"pair": f"{s1}-{s2}", "obs": obs_diff, "null_mean": null_diff_mean, "null_std": null_diff_std, "p": min(p, 1.0)})
    
    return {"results": {k: {kk: vv for kk, vv in v.items() if kk != "null_values"} for k, v in results.items()}, "contrasts": contrasts}

# ---- Structure correlation analysis ----

def run_structure_corr(records: dict[str, list[WindowRecord]]) -> dict:
    """Run Uplift vs Structure correlation analysis."""
    from scipy.stats import spearmanr
    
    def partial_corr(u, mfe, gc, dinuc):
        mask = ~(np.isnan(u) | np.isnan(mfe) | np.isnan(gc))
        if mask.sum() < 30: return float("nan"), float("nan")
        X = np.column_stack([gc[mask], dinuc[mask]])
        from numpy.linalg import lstsq
        cu, _, _, _ = lstsq(X, u[mask], rcond=None)
        cm, _, _, _ = lstsq(X, mfe[mask], rcond=None)
        r, p = spearmanr(u[mask] - X @ cu, mfe[mask] - X @ cm)
        return float(r), float(p)
    
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
        
        mask_b = ~(np.isnan(ub) | np.isnan(mb))
        mask_a = ~(np.isnan(ua) | np.isnan(ma))
        rb, pb = spearmanr(ub[mask_b], mb[mask_b]) if mask_b.sum() > 10 else (float("nan"), float("nan"))
        ra, pa = spearmanr(ua[mask_a], ma[mask_a]) if mask_a.sum() > 10 else (float("nan"), float("nan"))
        rpb, ppb = partial_corr(ub, mb, gb, db)
        rpa, ppa = partial_corr(ua, ma, ga, da)
        
        results[stop] = {
            "n": len(recs),
            "before": {"raw": {"r": float(rb), "p": float(pb)}, "partial": {"r": rpb, "p": ppb}},
            "after": {"raw": {"r": float(ra), "p": float(pa)}, "partial": {"r": rpa, "p": ppa}},
        }
    
    # Pooled
    ub, ua = np.array(all_ub), np.array(all_ua)
    mb, ma = np.array(all_mb), np.array(all_ma)
    gb, ga = np.array(all_gb), np.array(all_ga)
    db, da = np.array(all_db), np.array(all_da)
    
    mask_b = ~(np.isnan(ub) | np.isnan(mb))
    mask_a = ~(np.isnan(ua) | np.isnan(ma))
    rb, pb = spearmanr(ub[mask_b], mb[mask_b]) if mask_b.sum() > 10 else (float("nan"), float("nan"))
    ra, pa = spearmanr(ua[mask_a], ma[mask_a]) if mask_a.sum() > 10 else (float("nan"), float("nan"))
    rpb, ppb = partial_corr(ub, mb, gb, db)
    rpa, ppa = partial_corr(ua, ma, ga, da)
    
    results["pooled"] = {
        "n": len(ub),
        "before": {"raw": {"r": float(rb), "p": float(pb)}, "partial": {"r": rpb, "p": ppb}},
        "after": {"raw": {"r": float(ra), "p": float(pa)}, "partial": {"r": rpa, "p": ppa}},
    }
    
    return results

# ---- Main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10, help="Window radius in codons")
    ap.add_argument("--n-per-stop", type=int, default=1000, help="Sample size per stop class")
    ap.add_argument("--n-perm", type=int, default=100, help="Number of permutations for null")
    ap.add_argument("--seed", type=int, default=0, help="Random seed")
    ap.add_argument("--force", action="store_true", help="Force recomputation")
    args = ap.parse_args()
    
    out_dinuc = generated_dir() / "stop_context_window_dinuc_null.tex"
    out_struct = generated_dir() / "stop_context_window_structure_corr.tex"
    cache_file = cache_dir() / f"stop_context_window_analysis_v{ANALYSIS_VERSION}.json"
    
    meta = {"v": ANALYSIS_VERSION, "k": args.k, "n": args.n_per_stop, "perm": args.n_perm}
    
    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if cached.get("k") == args.k and cached.get("n_per_stop") == args.n_per_stop:
                print(f"[cache] Using cached results")
                _emit_outputs(cached, out_dinuc, out_struct, meta, args.k)
                return
        except: pass
    
    # Find FASTA files
    fasta_files = sorted(data_dir().glob("human.*.rna.fna.gz"))
    if not fasta_files:
        print(f"[error] No FASTA files found in {data_dir()}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[load] Loading from {len(fasta_files)} FASTA files...", flush=True)
    records = load_windows_from_fasta(fasta_files, args.k, args.n_per_stop, args.seed)
    
    # Run dinucleotide null
    print(f"[dinuc] Running dinucleotide shuffle null (n_perm={args.n_perm})...", flush=True)
    print("  before-window...", flush=True)
    dinuc_before = run_dinuc_null(records, args.n_perm, args.seed, "before")
    print("  after-window...", flush=True)
    dinuc_after = run_dinuc_null(records, args.n_perm, args.seed + 1, "after")
    
    # Run structure correlation
    print("[struct] Running structure correlation...", flush=True)
    struct_corr = run_structure_corr(records)
    
    # Save results
    output = {
        "k": args.k,
        "n_per_stop": args.n_per_stop,
        "n_perm": args.n_perm,
        "dinuc_before": dinuc_before,
        "dinuc_after": dinuc_after,
        "structure_corr": struct_corr,
    }
    write_json_atomic(cache_file, output)
    
    _emit_outputs(output, out_dinuc, out_struct, meta, args.k)

def _emit_outputs(output: dict, out_dinuc: Path, out_struct: Path, meta: dict, k: int):
    """Generate LaTeX outputs."""
    # Dinucleotide null summary
    db = output.get("dinuc_before", {})
    da = output.get("dinuc_after", {})
    n_perm = output.get("n_perm", 100)
    
    lines = [f"Dinucleotide-preserving window-level shuffle null ($k={k}$, n\\_perm={n_perm})."]
    
    for window, d in [("before", db), ("after", da)]:
        res = d.get("results", {})
        obs = "; ".join(f"{s}={res.get(s, {}).get('obs_mean', 0):.4f}" for s in ["UAA", "UAG", "UGA"])
        lines.append(f" {window.capitalize()}-window observed: {obs}.")
        
        con = d.get("contrasts", [])
        con_str = "; ".join(f"{c['pair']}={c['obs']:+.4f} (null {c['null_mean']:+.4f}$\\pm${c['null_std']:.4f}, p={c['p']:.4f})" for c in con)
        lines.append(f" Contrasts: {con_str}.")
    
    write_text_atomic(out_dinuc, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_dinuc), meta)
    print(f"Wrote: {out_dinuc}")
    
    # Structure correlation summary
    sc = output.get("structure_corr", {})
    p = sc.get("pooled", {})
    bb = p.get("before", {}).get("raw", {})
    bp = p.get("before", {}).get("partial", {})
    ab = p.get("after", {}).get("raw", {})
    ap_ = p.get("after", {}).get("partial", {})
    
    def f(x): return f"{x:.3f}" if x and not np.isnan(x) else "--"
    
    txt = (f"Uplift vs GC-proxy structure ($k={k}$, n={p.get('n', 0)}). "
           f"Before: raw $\\rho={f(bb.get('r'))}$ ($p={f(bb.get('p'))}$), "
           f"partial $\\rho={f(bp.get('r'))}$ ($p={f(bp.get('p'))}$). "
           f"After: raw $\\rho={f(ab.get('r'))}$ ($p={f(ab.get('p'))}$), "
           f"partial $\\rho={f(ap_.get('r'))}$ ($p={f(ap_.get('p'))}$).\n")
    
    # Table
    rows = ["\\begin{center}\\small\\begin{tabular}{lcccc}\\toprule",
            "Stop & raw$_b$ & partial$_b$ & raw$_a$ & partial$_a$ \\\\\\midrule"]
    for s in ["UAA", "UAG", "UGA", "pooled"]:
        r = sc.get(s, {})
        bb = r.get("before", {}).get("raw", {})
        bp = r.get("before", {}).get("partial", {})
        ab = r.get("after", {}).get("raw", {})
        ap_ = r.get("after", {}).get("partial", {})
        lbl = s if s != "pooled" else "\\textbf{Pooled}"
        rows.append(f"{lbl} & {f(bb.get('r'))} & {f(bp.get('r'))} & {f(ab.get('r'))} & {f(ap_.get('r'))} \\\\")
    rows.append("\\bottomrule\\end{tabular}\\end{center}")
    
    write_text_atomic(out_struct, txt + "\n".join(rows) + "\n")
    write_json_atomic(cache_meta_path(out_struct), meta)
    print(f"Wrote: {out_struct}")

if __name__ == "__main__":
    main()
