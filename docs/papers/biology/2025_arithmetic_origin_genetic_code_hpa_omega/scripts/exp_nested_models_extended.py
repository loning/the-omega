# -*- coding: utf-8 -*-
"""
Extended nested models (M0-M5) for recoding vs terminal-stop discrimination.

Extends the existing M0/M1/M2 analysis with:
- M3: M1 + structure features (GC-proxy for MFE)
- M4: M1 + structure + uplift
- M5: M1 + structure + uplift + tAI (translation rate)

This allows testing whether each feature block provides incremental
information beyond the previous model.

Output:
  - sections/generated/nested_models_extended_summary.tex
  - sections/generated/nested_models_extended_table.tex
"""

from __future__ import annotations
import argparse, gzip, json, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}
NUCS = "ACGU"
DINUCS = [a + b for a in NUCS for b in NUCS]

# Human tAI values (same as in exp_uplift_translation_rate_proxy.py)
HUMAN_TAI = {
    "UUU": 0.52, "UUC": 1.00, "UUA": 0.12, "UUG": 0.52, "CUU": 0.28, "CUC": 0.64, "CUA": 0.12, "CUG": 1.00,
    "AUU": 0.48, "AUC": 1.00, "AUA": 0.16, "AUG": 1.00,
    "GUU": 0.36, "GUC": 1.00, "GUA": 0.12, "GUG": 0.52,
    "UCU": 0.28, "UCC": 0.68, "UCA": 0.20, "UCG": 0.12, "AGU": 0.24, "AGC": 1.00,
    "CCU": 0.36, "CCC": 1.00, "CCA": 0.28, "CCG": 0.12,
    "ACU": 0.32, "ACC": 1.00, "ACA": 0.24, "ACG": 0.12,
    "GCU": 0.40, "GCC": 1.00, "GCA": 0.28, "GCG": 0.12,
    "UAU": 0.44, "UAC": 1.00, "CAU": 0.44, "CAC": 1.00,
    "CAA": 0.32, "CAG": 1.00, "AAU": 0.44, "AAC": 1.00,
    "AAA": 0.48, "AAG": 1.00, "GAU": 0.48, "GAC": 1.00,
    "GAA": 0.48, "GAG": 1.00, "UGU": 0.44, "UGC": 1.00,
    "UGG": 1.00,
    "CGU": 0.16, "CGC": 0.56, "CGA": 0.12, "CGG": 0.20, "AGA": 0.20, "AGG": 0.20,
    "GGU": 0.24, "GGC": 1.00, "GGA": 0.28, "GGG": 0.24,
    "UAA": 0.0, "UAG": 0.0, "UGA": 0.0,
}

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data"
def cache_dir():
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

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
    gc = gc_fraction(seq)
    return -0.5 * len(seq) * (gc - 0.3) if not np.isnan(gc) else float("nan")

def window_mean_uplift(seq: str) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    vals = []
    for c in codons:
        if c in GENETIC_CODE:
            try:
                cf = fold_codon(c, MU_STAR)
                vals.append(float(cf.delta))
            except: pass
    return float(np.mean(vals)) if vals else float("nan")

def window_mean_tai(seq: str) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    vals = [HUMAN_TAI.get(c, float("nan")) for c in codons if c in GENETIC_CODE]
    return float(np.nanmean(vals)) if vals else float("nan")

# ---- Data loading ----

def load_transl_except_data(cache_path: Path | None = None) -> list[dict] | None:
    """Try to load transl_except recoding data from existing cache."""
    if cache_path and cache_path.exists():
        try:
            with open(cache_path) as f:
                data = json.load(f)
            return data.get("events", [])
        except:
            pass
    return None

def load_refseq_terminal_stops(fasta_dir: Path, k: int, n_samples: int, seed: int) -> list[dict]:
    """Load terminal stop windows from RefSeq FASTA files."""
    rng = np.random.default_rng(seed)
    
    @dataclass
    class ORFInfo:
        start_base: int
        stop_base: int
        stop_codon: str
    
    def best_orf(seq: str) -> ORFInfo | None:
        seq = normalize_seq(seq)
        best = None
        best_len = 0
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
                if length > best_len:
                    best = ORFInfo(start_base=s, stop_base=stop_base, stop_codon=stop_codon)
                    best_len = length
        return best
    
    def _iter_fasta_handle(handle):
        header = None
        seq_parts = []
        for line in handle:
            line = line.strip()
            if line.startswith(">"):
                if header:
                    yield header, "".join(seq_parts)
                header = line[1:].split()[0]
                seq_parts = []
            else:
                seq_parts.append(line)
        if header:
            yield header, "".join(seq_parts)
    
    all_events = []
    fasta_files = sorted(fasta_dir.glob("human.*.rna.fna.gz"))
    
    for fasta_path in fasta_files:
        try:
            with gzip.open(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta_handle(f):
                    orf = best_orf(seq)
                    if not orf:
                        continue
                    
                    before_start = orf.stop_base - 3 * k
                    after_start = orf.stop_base + 3
                    
                    if before_start < orf.start_base:
                        continue
                    if after_start + 3 * k > len(seq):
                        continue
                    
                    before_seq = seq[before_start:orf.stop_base]
                    after_seq = seq[after_start:after_start + 3 * k]
                    
                    if len(before_seq) != 3 * k or len(after_seq) != 3 * k:
                        continue
                    
                    all_events.append({
                        "type": "terminal",
                        "stop_codon": orf.stop_codon,
                        "before_seq": before_seq,
                        "after_seq": after_seq,
                    })
        except Exception as e:
            print(f"  [warning] {fasta_path}: {e}")
    
    # Sample
    if len(all_events) > n_samples:
        idx = rng.choice(len(all_events), size=n_samples, replace=False)
        all_events = [all_events[i] for i in idx]
    
    return all_events

def compute_features(events: list[dict], k: int) -> dict:
    """Compute all features for each event."""
    X_stop = []  # Stop codon one-hot (3 classes: UAA, UAG, UGA)
    X_plus4 = []  # +4 base one-hot (4 classes)
    X_gc = []  # GC content (2 features: before, after)
    X_dinuc = []  # Dinucleotide (32 features: 16 before + 16 after)
    X_structure = []  # Structure proxy (2 features: before, after)
    X_uplift = []  # Uplift (3 features: before, after, diff)
    X_tai = []  # tAI (2 features: before, after)
    y = []  # Label (1=recoding, 0=terminal)
    groups = []  # CDS groups for CV
    
    stop_map = {"UAA": 0, "UAG": 1, "UGA": 2}
    base_map = {"A": 0, "C": 1, "G": 2, "U": 3, "T": 3}
    
    valid_count = 0
    for i, event in enumerate(events):
        before_seq = event.get("before_seq", "")
        after_seq = event.get("after_seq", "")
        stop = event.get("stop_codon", "")
        event_type = event.get("type", "terminal")
        
        if not before_seq or not after_seq or stop not in stop_map:
            continue
        
        # +4 base
        plus4 = after_seq[0] if after_seq else "N"
        if plus4 not in base_map:
            continue
        
        # Features
        u_before = window_mean_uplift(before_seq)
        u_after = window_mean_uplift(after_seq)
        tai_before = window_mean_tai(before_seq)
        tai_after = window_mean_tai(after_seq)
        gc_before = gc_fraction(before_seq)
        gc_after = gc_fraction(after_seq)
        dinuc_before = dinuc_freq(before_seq)
        dinuc_after = dinuc_freq(after_seq)
        struct_before = gc_structure_proxy(before_seq)
        struct_after = gc_structure_proxy(after_seq)
        
        if any(np.isnan(x) for x in [u_before, u_after, tai_before, tai_after, gc_before, gc_after]):
            continue
        
        # Stop one-hot
        stop_oh = [0, 0, 0]
        stop_oh[stop_map[stop]] = 1
        X_stop.append(stop_oh)
        
        # +4 one-hot
        plus4_oh = [0, 0, 0, 0]
        plus4_oh[base_map[plus4]] = 1
        X_plus4.append(plus4_oh)
        
        X_gc.append([gc_before, gc_after])
        X_dinuc.append(np.concatenate([dinuc_before, dinuc_after]))
        X_structure.append([struct_before, struct_after])
        X_uplift.append([u_before, u_after, u_after - u_before])
        X_tai.append([tai_before, tai_after])
        
        y.append(1 if event_type == "recoding" else 0)
        groups.append(event.get("cds_id", i))
        valid_count += 1
    
    return {
        "X_stop": np.array(X_stop),
        "X_plus4": np.array(X_plus4),
        "X_gc": np.array(X_gc),
        "X_dinuc": np.array(X_dinuc),
        "X_structure": np.array(X_structure),
        "X_uplift": np.array(X_uplift),
        "X_tai": np.array(X_tai),
        "y": np.array(y),
        "groups": np.array(groups),
        "n_valid": valid_count,
    }

def run_nested_models(features: dict, n_perm: int = 100, seed: int = 0) -> dict:
    """Run nested model comparison with group-aware CV."""
    from sklearn.model_selection import GroupKFold
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    
    rng = np.random.default_rng(seed)
    
    X_stop = features["X_stop"]
    X_plus4 = features["X_plus4"]
    X_gc = features["X_gc"]
    X_dinuc = features["X_dinuc"]
    X_structure = features["X_structure"]
    X_uplift = features["X_uplift"]
    X_tai = features["X_tai"]
    y = features["y"]
    groups = features["groups"]
    
    # Model definitions
    models = {
        "M0": np.hstack([X_stop, X_plus4]),  # Stop + +4 base
        "M1": np.hstack([X_stop, X_plus4, X_gc, X_dinuc]),  # M0 + GC + dinuc
        "M2": np.hstack([X_stop, X_plus4, X_gc, X_dinuc, X_uplift]),  # M1 + uplift
        "M3": np.hstack([X_stop, X_plus4, X_gc, X_dinuc, X_structure]),  # M1 + structure
        "M4": np.hstack([X_stop, X_plus4, X_gc, X_dinuc, X_structure, X_uplift]),  # M3 + uplift
        "M5": np.hstack([X_stop, X_plus4, X_gc, X_dinuc, X_structure, X_uplift, X_tai]),  # M4 + tAI
    }
    
    def cv_auc(X, y, groups, seed):
        gkf = GroupKFold(n_splits=5)
        aucs = []
        model = LogisticRegression(max_iter=2000, solver="lbfgs", n_jobs=1)
        for tr, te in gkf.split(X, y, groups):
            if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
                continue
            model.fit(X[tr], y[tr])
            p = model.predict_proba(X[te])[:, 1]
            aucs.append(roc_auc_score(y[te], p))
        return float(np.mean(aucs)) if aucs else 0.5
    
    # Compute AUCs
    aucs = {}
    for name, X in models.items():
        aucs[name] = cv_auc(X, y, groups, seed)
        print(f"  {name}: AUC={aucs[name]:.4f}", flush=True)
    
    # Permutation tests for incremental improvements
    deltas = {
        "M1-M0": aucs["M1"] - aucs["M0"],
        "M2-M1": aucs["M2"] - aucs["M1"],
        "M3-M1": aucs["M3"] - aucs["M1"],
        "M4-M3": aucs["M4"] - aucs["M3"],
        "M5-M4": aucs["M5"] - aucs["M4"],
    }
    
    # Simplified permutation test (permute the added features)
    def perm_test(X_base, X_add, y, groups, obs_delta, n_perm, rng):
        ge = 0
        for _ in range(n_perm):
            perm = rng.permutation(len(y))
            X_perm = np.hstack([X_base, X_add[perm]])
            auc_perm = cv_auc(X_perm, y, groups, 0)
            auc_base = cv_auc(X_base, y, groups, 0)
            if auc_perm - auc_base >= obs_delta:
                ge += 1
        return (ge + 1) / (n_perm + 1)
    
    p_values = {}
    print("  Running permutation tests...", flush=True)
    
    # M2-M1: test uplift block
    p_values["M2-M1"] = perm_test(models["M1"], X_uplift, y, groups, deltas["M2-M1"], n_perm, rng)
    # M3-M1: test structure block
    p_values["M3-M1"] = perm_test(models["M1"], X_structure, y, groups, deltas["M3-M1"], n_perm, rng)
    # M4-M3: test uplift after structure
    p_values["M4-M3"] = perm_test(models["M3"], X_uplift, y, groups, deltas["M4-M3"], n_perm, rng)
    # M5-M4: test tAI after everything
    p_values["M5-M4"] = perm_test(models["M4"], X_tai, y, groups, deltas["M5-M4"], n_perm, rng)
    
    return {
        "aucs": aucs,
        "deltas": deltas,
        "p_values": p_values,
        "n_samples": len(y),
        "n_positive": int(y.sum()),
        "n_negative": int(len(y) - y.sum()),
    }

# ---- Load real recoding data ----

def load_recoding_jsonl(jsonl_path: Path, k: int) -> tuple[list[dict], list[dict]]:
    """Load recoding sites and corresponding terminal stops from JSONL."""
    recoding_events = []
    terminal_events = []
    seen_cds = set()
    
    with open(jsonl_path) as f:
        for line in f:
            rec = json.loads(line.strip())
            
            # Check k matches
            if rec.get("k") != k:
                continue
            
            cds_id = f"{rec.get('gene', '')}_{rec.get('organism', '')}"
            
            # Recoding site
            before_seq = (rec.get("before_seq_dna") or "").upper().replace("T", "U")
            after_seq = (rec.get("after_seq_dna") or "").upper().replace("T", "U")
            stop_codon = rec.get("codon_rna") or ""
            
            if before_seq and after_seq and stop_codon in STOP_CODONS:
                recoding_events.append({
                    "type": "recoding",
                    "stop_codon": stop_codon,
                    "before_seq": before_seq,
                    "after_seq": after_seq,
                    "cds_id": cds_id,
                    "plus4": rec.get("plus4_nt", "N"),
                })
            
            # Terminal stop (one per CDS)
            if cds_id not in seen_cds:
                term_before = (rec.get("terminal_before_seq_dna") or "").upper().replace("T", "U")
                term_after = (rec.get("terminal_after_seq_dna") or "").upper().replace("T", "U")
                term_stop = rec.get("terminal_stop") or ""
                
                if term_before and term_after and term_stop in STOP_CODONS:
                    terminal_events.append({
                        "type": "terminal",
                        "stop_codon": term_stop,
                        "before_seq": term_before,
                        "after_seq": term_after,
                        "cds_id": cds_id,
                        "plus4": term_after[0] if term_after else "N",
                    })
                    seen_cds.add(cds_id)
    
    return recoding_events, terminal_events

# ---- Main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n-perm", type=int, default=50, help="Number of permutations")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    out_summary = generated_dir() / "nested_models_extended_summary.tex"
    out_table = generated_dir() / "nested_models_extended_table.tex"
    cache_file = cache_dir() / f"nested_models_extended_v{ANALYSIS_VERSION}.json"
    meta = {"v": ANALYSIS_VERSION, "k": args.k}
    
    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if cached.get("k") == args.k:
                print("[cache] Using cached results")
                _emit(cached, out_summary, out_table, meta, args.k)
                return
        except: pass
    
    # Load real recoding data
    jsonl_path = data_dir() / "recoding_genbank" / "recoding_sites.jsonl"
    if not jsonl_path.exists():
        print(f"[error] Recoding data not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[load] Loading recoding data from {jsonl_path}...", flush=True)
    recoding_events, terminal_events = load_recoding_jsonl(jsonl_path, args.k)
    print(f"  Recoding sites: {len(recoding_events)}", flush=True)
    print(f"  Terminal stops: {len(terminal_events)}", flush=True)
    
    # Combine events
    events = recoding_events + terminal_events
    
    if not events:
        print("[error] No events loaded", file=sys.stderr)
        sys.exit(1)
    
    # Compute features
    print("[compute] Computing features...", flush=True)
    features = compute_features(events, args.k)
    
    n_pos = int(features["y"].sum())
    n_neg = int(len(features["y"]) - n_pos)
    print(f"  n={features['n_valid']}, n_recoding={n_pos}, n_terminal={n_neg}", flush=True)
    
    # Run models
    print("[models] Running nested model comparison...", flush=True)
    results = run_nested_models(features, args.n_perm, args.seed)
    results["k"] = args.k
    results["task"] = "recoding_vs_terminal"
    
    write_json_atomic(cache_file, results)
    _emit(results, out_summary, out_table, meta, args.k)

def _emit(results: dict, out_summary: Path, out_table: Path, meta: dict, k: int):
    """Generate LaTeX outputs."""
    aucs = results.get("aucs", {})
    deltas = results.get("deltas", {})
    p_values = results.get("p_values", {})
    n = results.get("n_samples", 0)
    
    def f(x): return f"{x:.4f}" if x and not np.isnan(x) else "--"
    
    task_desc = results.get("task", "unknown")
    
    lines = [
        f"\\paragraph{{Extended nested models ($k={k}$, n={n}, task={task_desc}).}}",
        "Model hierarchy: M0 (stop+plus4) $\\subset$ M1 (+GC+dinuc) $\\subset$ M2 (+uplift) / M3 (+structure) $\\subset$ M4 (+both) $\\subset$ M5 (+tAI).",
        f"AUCs: M0={f(aucs.get('M0'))}, M1={f(aucs.get('M1'))}, M2={f(aucs.get('M2'))}, M3={f(aucs.get('M3'))}, M4={f(aucs.get('M4'))}, M5={f(aucs.get('M5'))}.",
    ]
    
    # Incremental improvements
    lines.append("Incremental improvements (permutation test):")
    for key in ["M2-M1", "M3-M1", "M4-M3", "M5-M4"]:
        d = deltas.get(key, 0)
        p = p_values.get(key, 1)
        lines.append(f"  $\\Delta$AUC$_{{{key}}}$={f(d)}, $p$={f(p)};")
    
    write_text_atomic(out_summary, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_summary), meta)
    print(f"Wrote: {out_summary}")
    
    # Table
    table = [
        "\\begin{center}\\small",
        "\\begin{tabular}{lcccc}\\toprule",
        "Model & Features & AUC & $\\Delta$AUC & $p$ \\\\\\midrule",
    ]
    
    model_features = {
        "M0": "stop + +4",
        "M1": "M0 + GC + dinuc",
        "M2": "M1 + uplift",
        "M3": "M1 + structure",
        "M4": "M3 + uplift",
        "M5": "M4 + tAI",
    }
    
    prev_model = {"M1": "M0", "M2": "M1", "M3": "M1", "M4": "M3", "M5": "M4"}
    
    for m in ["M0", "M1", "M2", "M3", "M4", "M5"]:
        auc = aucs.get(m, 0)
        if m in prev_model:
            key = f"{m}-{prev_model[m]}"
            d = deltas.get(key, 0)
            p = p_values.get(key, float("nan"))
            table.append(f"{m} & {model_features[m]} & {f(auc)} & {f(d)} & {f(p)} \\\\")
        else:
            table.append(f"{m} & {model_features[m]} & {f(auc)} & -- & -- \\\\")
    
    table.extend(["\\bottomrule\\end{tabular}", "\\end{center}"])
    
    write_text_atomic(out_table, "\n".join(table) + "\n")
    write_json_atomic(cache_meta_path(out_table), meta)
    print(f"Wrote: {out_table}")

if __name__ == "__main__":
    main()
