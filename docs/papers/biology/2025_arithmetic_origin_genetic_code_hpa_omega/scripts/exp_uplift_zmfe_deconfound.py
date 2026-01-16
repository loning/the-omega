# -*- coding: utf-8 -*-
"""
Uplift vs zMFE (composition-conditioned structure) around terminal stops.

Motivation (M3 / H3-1):
  Raw MFE is strongly mediated by composition (GC/dinuc). To test whether the
  uplift-window statistic U carries any *independent* structure signal, we
  compute a dinucleotide-matched shuffle null per window and convert MFE to a
  z-score:

    zMFE = (MFE_real - mean(MFE_shuffle)) / std(MFE_shuffle)

We then test association between U_after (and a GC+dinuc residual U_resid) and
zMFE at multiple stop-proximal after-window scales.

Inputs:
  - data/refseq_hsapiens_mrna/human.*.rna.fna.gz (RefSeq mRNA FASTA shards)
  - data/manifest.json (optional; used for dataset fingerprinting)

Outputs:
  - data/_cache/uplift_zmfe_deconfound_v1.json (+ meta)
  - sections/generated/uplift_zmfe_deconfound.tex
  - sections/generated/uplift_zmfe_deconfound_table.tex
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon


ANALYSIS_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}
NUCS = "ACGU"
DINUCS = [a + b for a in NUCS for b in NUCS]


def root_dir() -> Path:
    return SCRIPT_DIR.parent


def data_dir() -> Path:
    return root_dir() / "data" / "refseq_hsapiens_mrna"


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_json_dict(path: Path) -> dict[str, object] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _refseq_fingerprint() -> str:
    """
    Prefer manifest-provided sha256s; fall back to file stats.
    """
    mp = root_dir() / "data" / "manifest.json"
    if mp.exists():
        m = _read_json_dict(mp)
        ds = None
        if isinstance(m, dict):
            datasets = m.get("datasets")
            if isinstance(datasets, dict):
                ds = datasets.get("refseq_hsapiens_mrna")
        if isinstance(ds, dict):
            files = ds.get("files")
            pairs: list[tuple[str, str]] = []
            if isinstance(files, list):
                for e in files:
                    if not isinstance(e, dict):
                        continue
                    name = e.get("name")
                    sha = e.get("sha256")
                    if isinstance(name, str) and isinstance(sha, str) and name and sha:
                        pairs.append((name, sha))
            if pairs:
                pairs.sort()
                return f"manifest_sha:{cache_key_digest(pairs)}"

    fps: list[tuple[str, int, int]] = []
    for fp in sorted(data_dir().glob("human.*.rna.fna.gz")):
        try:
            st = fp.stat()
        except FileNotFoundError:
            continue
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
        fps.append((fp.name, int(st.st_size), int(mtime_ns)))
    return f"stat:{cache_key_digest(fps)}"


def normalize_seq(seq: str) -> str:
    return seq.upper().replace("T", "U")


def _is_valid_rna(seq: str) -> bool:
    s = normalize_seq(seq)
    return bool(s) and all(ch in NUCS for ch in s)


def gc_fraction(seq: str) -> float:
    s = normalize_seq(seq)
    if not s:
        return float("nan")
    return sum(1 for ch in s if ch in "GC") / len(s)


def dinuc_freq(seq: str) -> np.ndarray:
    s = normalize_seq(seq)
    idx = {d: i for i, d in enumerate(DINUCS)}
    counts = np.zeros(16, dtype=float)
    for i in range(len(s) - 1):
        d = s[i : i + 2]
        if d[0] in NUCS and d[1] in NUCS:
            counts[idx[d]] += 1.0
    if counts.sum() > 0:
        counts /= counts.sum()
    return counts


def window_mean_uplift(seq: str) -> float:
    s = normalize_seq(seq)
    codons = [s[i : i + 3] for i in range(0, len(s) - 2, 3)]
    vals = []
    for c in codons:
        if c in GENETIC_CODE:
            try:
                cf = fold_codon(c, MU_STAR)
                vals.append(float(cf.delta))
            except Exception:
                pass
    return float(np.mean(vals)) if vals else float("nan")


def dinuc_shuffle(seq: str, rng: np.random.Generator) -> str:
    """
    Dinucleotide-preserving shuffle via an Eulerian trail (Hierholzer).
    """
    s = normalize_seq(seq)
    if len(s) <= 2:
        return s
    edges = {b: [] for b in NUCS}
    for i in range(len(s) - 1):
        a, b = s[i], s[i + 1]
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
    return "".join(reversed(path))[: len(s)]


def compute_mfe(seq: str) -> float:
    try:
        import RNA

        s = normalize_seq(seq).replace("U", "T")
        fc = RNA.fold_compound(s)
        _, mfe = fc.mfe()
        return float(mfe)
    except Exception:
        return float("nan")


def _subseed(seed: int, *, ws: int, i: int) -> int:
    return int((int(seed) + 1000003 * int(ws) + 9176 * int(i)) % (2**32))


def compute_zmfe(seq: str, *, seed: int, ws: int, i: int, n_shuffles: int) -> dict[str, float]:
    mfe0 = compute_mfe(seq)
    if np.isnan(mfe0) or n_shuffles <= 0:
        return {"mfe": float(mfe0), "zmfe": float("nan"), "mfe_shuf_mean": float("nan"), "mfe_shuf_std": float("nan")}
    rng = np.random.default_rng(_subseed(seed, ws=ws, i=i))
    mfes = []
    for _ in range(int(n_shuffles)):
        sh = dinuc_shuffle(seq, rng)
        mfes.append(compute_mfe(sh))
    arr = np.asarray(mfes, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < max(3, int(n_shuffles) // 2):
        return {"mfe": float(mfe0), "zmfe": float("nan"), "mfe_shuf_mean": float("nan"), "mfe_shuf_std": float("nan")}
    mu = float(arr.mean())
    sd = float(arr.std(ddof=1)) if arr.size >= 2 else 0.0
    if not np.isfinite(sd) or sd <= 0:
        z = float("nan")
    else:
        z = float((float(mfe0) - mu) / sd)
    return {"mfe": float(mfe0), "zmfe": z, "mfe_shuf_mean": mu, "mfe_shuf_std": float(sd)}


@dataclass(frozen=True)
class ORFInfo:
    start_base: int
    stop_base: int
    stop_codon: str


def best_orf(seq: str) -> ORFInfo | None:
    s = normalize_seq(seq)
    best = None
    best_len = 0
    for frame in range(3):
        orfs = find_orfs(s, frame=frame, min_codons=10)
        for (start, end) in orfs:
            length = (end - start) // 3
            stop_base = start + length * 3
            if stop_base + 3 > len(s):
                continue
            stop = s[stop_base : stop_base + 3]
            if stop not in STOP_CODONS:
                continue
            if length > best_len:
                best = ORFInfo(start_base=int(start), stop_base=int(stop_base), stop_codon=str(stop))
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


def load_after_windows(*, window_sizes: list[int], n_samples: int, seed: int) -> list[dict[str, object]]:
    rng = np.random.default_rng(int(seed))
    max_ws = max(window_sizes)
    collected: list[dict[str, object]] = []
    scanned = 0

    fasta_files = sorted(data_dir().glob("human.*.rna.fna.gz"))
    if not fasta_files:
        raise SystemExit("Missing RefSeq shards under data/refseq_hsapiens_mrna/. Run scripts/fetch_datasets.py --dataset refseq_hsapiens_mrna.")

    for fasta_path in fasta_files:
        if len(collected) >= int(n_samples) * 5:
            break
        with gzip.open(fasta_path, "rt") as f:
            for _, seq in _iter_fasta_handle(f):
                scanned += 1
                orf = best_orf(seq)
                if not orf:
                    continue
                after_start = int(orf.stop_base) + 3
                if after_start + max_ws > len(seq):
                    continue
                windows: dict[int, str] = {}
                ok = True
                for ws in window_sizes:
                    s = normalize_seq(seq[after_start : after_start + int(ws)])
                    if len(s) != int(ws) or (not _is_valid_rna(s)):
                        ok = False
                        break
                    windows[int(ws)] = s
                if not ok:
                    continue
                collected.append({"stop": orf.stop_codon, "windows": windows})
                if len(collected) >= int(n_samples) * 5:
                    break

    if len(collected) > int(n_samples):
        idx = rng.choice(len(collected), size=int(n_samples), replace=False)
        collected = [collected[int(i)] for i in idx]

    if not collected:
        raise SystemExit("Failed to collect any usable stop-after windows.")
    return collected


def _ols_r2(y: np.ndarray, X: np.ndarray) -> float:
    if y.size == 0:
        return float("nan")
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    if ss_tot <= 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def analyze(entries: list[dict[str, object]], *, window_sizes: list[int], seed: int, n_shuffles: int) -> dict[str, object]:
    out: dict[str, object] = {"windows": {}, "n_entries": int(len(entries))}
    for ws in window_sizes:
        u = []
        gc = []
        zmfe = []
        mfe = []
        din = []
        for i, e in enumerate(entries):
            windows = e.get("windows")
            if not isinstance(windows, dict):
                continue
            seq = windows.get(int(ws))
            if not isinstance(seq, str) or not _is_valid_rna(seq):
                continue
            u0 = window_mean_uplift(seq)
            gc0 = gc_fraction(seq)
            din0 = dinuc_freq(seq)
            z = compute_zmfe(seq, seed=int(seed), ws=int(ws), i=int(i), n_shuffles=int(n_shuffles))

            if any(np.isnan(x) for x in [u0, gc0, float(z["mfe"]), float(z["zmfe"])]):
                continue
            u.append(float(u0))
            gc.append(float(gc0))
            din.append(din0)
            mfe.append(float(z["mfe"]))
            zmfe.append(float(z["zmfe"]))

        u = np.asarray(u, dtype=float)
        gc = np.asarray(gc, dtype=float)
        mfe = np.asarray(mfe, dtype=float)
        zmfe = np.asarray(zmfe, dtype=float)
        din = np.asarray(din, dtype=float)
        n = int(u.size)
        if n < 50:
            out["windows"][int(ws)] = {"n": n, "error": "insufficient data"}
            continue

        # U residualized by GC+dinuc (linear), then correlate with zMFE.
        X_base = np.column_stack([np.ones(n), gc, din])
        beta_u, _, _, _ = np.linalg.lstsq(X_base, u, rcond=None)
        u_resid = u - X_base @ beta_u

        # Correlations
        r_mfe, p_mfe = spearmanr(u, mfe)
        r_zmfe, p_zmfe = spearmanr(u, zmfe)
        r_ures_zmfe, p_ures_zmfe = spearmanr(u_resid, zmfe)

        # Regression: zMFE ~ GC+dinuc (+U)
        r2_z_base = _ols_r2(zmfe, X_base)
        X_full = np.column_stack([X_base, u])
        r2_z_full = _ols_r2(zmfe, X_full)

        out["windows"][int(ws)] = {
            "n": n,
            "spearman": {
                "u_mfe": {"r": float(r_mfe), "p": float(p_mfe)},
                "u_zmfe": {"r": float(r_zmfe), "p": float(p_zmfe)},
                "u_resid_zmfe": {"r": float(r_ures_zmfe), "p": float(p_ures_zmfe)},
            },
            "regression": {
                "r2_zmfe_base": float(r2_z_base),
                "r2_zmfe_full": float(r2_z_full),
                "delta_r2_u_to_zmfe": float(r2_z_full - r2_z_base),
            },
            "means": {"u": float(np.mean(u)), "gc": float(np.mean(gc)), "mfe": float(np.mean(mfe)), "zmfe": float(np.mean(zmfe))},
        }

    return out


def _emit_latex(summary: dict[str, object], *, out_tex: Path, out_table: Path, meta: dict[str, object]) -> None:
    def f(x: object) -> str:
        try:
            v = float(x)  # type: ignore[arg-type]
        except Exception:
            return "--"
        if not np.isfinite(v):
            return "--"
        return f"{v:.3f}"

    def p_fmt(p: object) -> str:
        try:
            v = float(p)  # type: ignore[arg-type]
        except Exception:
            return "--"
        if not np.isfinite(v):
            return "--"
        if v < 0.001:
            return "$<$0.001"
        return f"{v:.3f}"

    windows = summary.get("windows")
    if not isinstance(windows, dict):
        windows = {}

    lines = []
    lines.append("\\paragraph{Composition-conditioned structure: zMFE (dinucleotide-matched shuffle null).}")
    lines.append(
        "For each stop-proximal after-window we compute MFE and zMFE, where zMFE is defined as the per-window z-score"
        " of the real MFE against a dinucleotide-preserving shuffle null."
    )
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)

    table = []
    table.append("\\begin{center}\\small")
    table.append("\\begin{tabular}{lccccc}\\toprule")
    table.append("Window & $n$ & $\\rho(U,\\mathrm{MFE})$ & $\\rho(U,\\mathrm{zMFE})$ & $\\rho(U_{\\mathrm{resid}},\\mathrm{zMFE})$ & $\\Delta R^2_{U\\to \\mathrm{zMFE}}$ \\\\")
    table.append("\\midrule")
    for ws in sorted(windows.keys(), key=lambda x: int(x)):
        r = windows.get(ws)
        if not isinstance(r, dict) or "spearman" not in r:
            continue
        sp = r.get("spearman") if isinstance(r.get("spearman"), dict) else {}
        reg = r.get("regression") if isinstance(r.get("regression"), dict) else {}
        table.append(
            f"{int(ws)}nt & {int(r.get('n',0) or 0)} & {f((sp.get('u_mfe') or {}).get('r'))} & "
            f"{f((sp.get('u_zmfe') or {}).get('r'))} & {f((sp.get('u_resid_zmfe') or {}).get('r'))} & "
            f"{f(reg.get('delta_r2_u_to_zmfe'))} \\\\"
        )
    table.append("\\bottomrule")
    table.append(
        "\\multicolumn{6}{l}{\\footnotesize $U_{\\mathrm{resid}}$: residual of $U$ after linear regression on GC+dinucleotide frequencies.} \\\\"
    )
    table.append("\\end{tabular}")
    table.append("\\end{center}")
    write_text_atomic(out_table, "\n".join(table) + "\n")
    write_json_atomic(cache_meta_path(out_table), meta)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Uplift vs zMFE deconfounding (dinuc shuffle null)")
    ap.add_argument("--window-sizes", type=str, default="30,60,120", help="Comma-separated window sizes in nt (after stop).")
    ap.add_argument("--n-samples", type=int, default=300, help="Number of sampled stop-after windows.")
    ap.add_argument("--n-shuffles", type=int, default=50, help="Number of dinuc shuffles per window for zMFE.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    window_sizes = [int(x) for x in str(args.window_sizes).split(",") if str(x).strip()]
    if not window_sizes:
        raise SystemExit("No window sizes provided.")

    out_json = cache_dir() / f"uplift_zmfe_deconfound_v{int(ANALYSIS_VERSION)}.json"
    out_tex = generated_dir() / "uplift_zmfe_deconfound.tex"
    out_table = generated_dir() / "uplift_zmfe_deconfound_table.tex"

    cache_key = {
        "analysis": "uplift_zmfe_deconfound",
        "analysis_version": int(ANALYSIS_VERSION),
        "refseq": _refseq_fingerprint(),
        "window_sizes": window_sizes,
        "n_samples": int(args.n_samples),
        "n_shuffles": int(args.n_shuffles),
        "seed": int(args.seed),
        "shuffle": "dinuc_eulerian",
    }
    meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_json, expected_meta=meta, require_meta=True):
        cached = read_json(out_json)
        _emit_latex(cached, out_tex=out_tex, out_table=out_table, meta=meta)
        return

    entries = load_after_windows(window_sizes=window_sizes, n_samples=int(args.n_samples), seed=int(args.seed))
    summary = analyze(entries, window_sizes=window_sizes, seed=int(args.seed), n_shuffles=int(args.n_shuffles))
    summary.update({"ok": True, "analysis_version": int(ANALYSIS_VERSION), "params": cache_key})

    write_json_atomic(out_json, summary)
    write_json_atomic(cache_meta_path(out_json), meta)
    _emit_latex(summary, out_tex=out_tex, out_table=out_table, meta=meta)
    print(f"Wrote: {out_tex}")
    print(f"Wrote: {out_table}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()
