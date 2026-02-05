#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cyclic-vs-boundary projection for X_n and its pi-channel (periodic-orbit) meaning.

This script upgrades the set-level split:
  X_n = X_n^{cyc} ⊔ X_n^{bdry},
where X_n is the golden-mean admissible language (no '11'), and
  X_n^{bdry} := { w in X_n : w_1=1 and w_n=1 }
  X_n^{cyc}  := X_n \\ X_n^{bdry}

into explicit linear projections on R^{X_n}:
  P_cyc  = diag(1_{w in X_n^{cyc}})
  P_bdry = diag(1_{w in X_n^{bdry}}).

We then connect this to the pi-channel (periodic-orbit / zeta counting) by using the
n-block presentation of the golden-mean shift:
  vertices: X_n
  edges:    w -> w' iff w'[0:n-1] = w[1:n] and w' is admissible.

Key audited facts:
  - pi-channel at resolution n is the length-n loop test in the n-block graph:
      w in X_n^{cyc}  <=>  (B^n)[w,w] > 0,
      w in X_n^{bdry} <=>  (B^n)[w,w] = 0.
    In particular:
      Tr(B^n) = Tr((P_cyc B P_cyc)^n) = |X_n^{cyc}|,
      Tr((P_bdry B P_bdry)^n) = 0.
  - for n=6, this gives the rigid 18 ⊕ 3 split used in the manuscript.

Artifacts:
  artifacts/x6_cyc_bdry_pi_channel_projection/<run_id>/result.json
  artifacts/x6_cyc_bdry_pi_channel_projection/<run_id>/adjacency.csv

Generated LaTeX:
  sections/generated/eq_x6_cyc_bdry_pi_channel_projection.tex
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir


def _phi() -> float:
    return (1.0 + math.sqrt(5.0)) / 2.0


def _fib_upto(n: int) -> List[int]:
    # F_1=F_2=1
    if n <= 0:
        return []
    if n == 1:
        return [1]
    f = [1, 1]
    while len(f) < n:
        f.append(f[-1] + f[-2])
    return f


def _F(k: int) -> int:
    if k <= 0:
        raise ValueError("k must be >= 1")
    return _fib_upto(k)[-1]


def golden_words(n: int) -> List[str]:
    """Lexicographically sorted length-n binary words with no adjacent ones."""
    if n < 0:
        raise ValueError("n must be >= 0")
    out: List[str] = []

    def rec(pos: int, prev1: int, acc: List[str]) -> None:
        if pos == n:
            out.append("".join(acc))
            return
        # choose 0
        acc.append("0")
        rec(pos + 1, 0, acc)
        acc.pop()
        # choose 1 if previous was 0
        if prev1 == 0:
            acc.append("1")
            rec(pos + 1, 1, acc)
            acc.pop()

    rec(0, 0, [])
    return sorted(out)


def split_cyc_bdry(words: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Return (cyc, bdry) split for X_n."""
    cyc: List[str] = []
    bdry: List[str] = []
    for w in words:
        if len(w) == 0:
            cyc.append(w)
            continue
        if w[0] == "1" and w[-1] == "1":
            bdry.append(w)
        else:
            cyc.append(w)
    return cyc, bdry


def build_nblock_adjacency(words: Sequence[str]) -> np.ndarray:
    """Return B (|X_n|x|X_n|) adjacency matrix of the n-block golden-mean shift."""
    idx = {w: i for i, w in enumerate(words)}
    n = len(words[0]) if words else 0
    B = np.zeros((len(words), len(words)), dtype=int)
    for w in words:
        i = idx[w]
        if n == 0:
            # single empty word with a self-loop
            B[i, i] = 1
            continue
        suf = w[1:]
        # append 0 always allowed
        w0 = suf + "0"
        j0 = idx[w0]
        B[i, j0] += 1
        # append 1 allowed iff last bit is 0
        if w[-1] == "0":
            w1 = suf + "1"
            j1 = idx[w1]
            B[i, j1] += 1
    return B


def spectral_radius(A: np.ndarray) -> float:
    vals = np.linalg.eigvals(A.astype(float))
    return float(np.max(np.abs(vals)))


def trace_powers(A: np.ndarray, k_max: int) -> List[int]:
    """Exact trace list Tr(A^k) for k=1..k_max using Python ints."""
    if k_max <= 0:
        return []
    # Use object dtype for exact integer arithmetic.
    P = A.astype(object)
    out: List[int] = []
    for k in range(1, k_max + 1):
        if k > 1:
            P = P @ A.astype(object)
        out.append(int(np.trace(P)))
    return out


@dataclass(frozen=True)
class Result:
    n: int
    X_size: int
    X_cyc_size: int
    X_bdry_size: int
    fib_total_F_nplus2: int
    fib_bdry_F_nminus2: int
    eps_ratio_bdry_over_total: float
    rho_full: float
    rho_cyc: float
    rho_bdry: float
    trace_full: List[int]
    trace_cyc: List[int]
    trace_bdry: List[int]
    trace_diff_full_minus_cyc: List[int]
    diag_B_pow_n: List[int]
    trace_B_pow_n: int
    trace_cyc_pow_n: int
    trace_bdry_pow_n: int
    audit_diag_support_equals_cyc: bool
    audit_trace_at_n_ok: bool
    bdry_words: List[str]
    cyc_words_head: List[str]


def main() -> None:
    ap = argparse.ArgumentParser(description="X_n cyc/bdry projection + pi-channel audit via n-block graph.")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--k-max", type=int, default=20, help="Max k for trace(B^k) audits.")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    n = int(args.n)
    k_max = int(args.k_max)
    if n <= 0:
        raise SystemExit("--n must be >= 1")
    if k_max < 1:
        raise SystemExit("--k-max must be >= 1")
    if k_max < n:
        raise SystemExit("--k-max must be >= n (needed for the pi-channel trace(B^n) audit)")

    script_path = Path(__file__).resolve()
    params: Dict[str, object] = {"n": n, "k_max": k_max}
    required = ["result.json", "adjacency.csv"]
    run = prepare_run(
        "x6_cyc_bdry_pi_channel_projection",
        params=params,
        script_path=script_path,
        required_files=required,
        force=bool(args.force),
    )

    if not run.cached:
        words = golden_words(n)
        cyc, bdry = split_cyc_bdry(words)
        B = build_nblock_adjacency(words)

        # Induced submatrices
        idx = {w: i for i, w in enumerate(words)}
        cyc_idx = [idx[w] for w in cyc]
        bdry_idx = [idx[w] for w in bdry]
        B_cyc = B[np.ix_(cyc_idx, cyc_idx)]
        B_bdry = B[np.ix_(bdry_idx, bdry_idx)]

        # Spectral radii
        rho_full = spectral_radius(B)
        rho_cyc = spectral_radius(B_cyc) if len(cyc_idx) > 0 else 0.0
        rho_bdry = spectral_radius(B_bdry) if len(bdry_idx) > 0 else 0.0

        # Trace audits: boundary should contribute nothing to periodic-orbit channel
        tr_full = trace_powers(B, k_max=k_max)
        tr_cyc = trace_powers(B_cyc, k_max=k_max) if len(cyc_idx) > 0 else [0] * k_max
        tr_bdry = trace_powers(B_bdry, k_max=k_max) if len(bdry_idx) > 0 else [0] * k_max
        tr_diff = [int(a - b) for a, b in zip(tr_full, tr_cyc)]

        # --- Pi-channel audit at resolution n: diagonal of B^n selects X_n^{cyc}. ---
        Bobj = B.astype(object)
        Pn = Bobj
        for _ in range(2, n + 1):
            Pn = Pn @ Bobj
        diag = [int(Pn[i, i]) for i in range(len(words))]
        diag_support = {i for i, v in enumerate(diag) if v != 0}
        cyc_set = set(cyc_idx)
        bdry_set = set(bdry_idx)
        audit_diag = (diag_support == cyc_set) and (len(diag_support & bdry_set) == 0)

        tr_full_n = int(tr_full[n - 1])
        tr_cyc_n = int(tr_cyc[n - 1]) if len(tr_cyc) >= n else 0
        tr_bdry_n = int(tr_bdry[n - 1]) if len(tr_bdry) >= n else 0
        audit_trace = (tr_full_n == tr_cyc_n == len(cyc)) and (tr_bdry_n == 0)

        # Fibonacci count checks: |X_n|=F_{n+2}, |X_n^{bdry}|=F_{n-2}
        fib_total = _F(n + 2)
        fib_bdry = _F(n - 2) if n >= 3 else 0
        eps_ratio = (len(bdry) / len(words)) if len(words) > 0 else float("nan")

        res = Result(
            n=n,
            X_size=len(words),
            X_cyc_size=len(cyc),
            X_bdry_size=len(bdry),
            fib_total_F_nplus2=int(fib_total),
            fib_bdry_F_nminus2=int(fib_bdry),
            eps_ratio_bdry_over_total=float(eps_ratio),
            rho_full=float(rho_full),
            rho_cyc=float(rho_cyc),
            rho_bdry=float(rho_bdry),
            trace_full=[int(x) for x in tr_full],
            trace_cyc=[int(x) for x in tr_cyc],
            trace_bdry=[int(x) for x in tr_bdry],
            trace_diff_full_minus_cyc=[int(x) for x in tr_diff],
            diag_B_pow_n=[int(x) for x in diag],
            trace_B_pow_n=int(tr_full_n),
            trace_cyc_pow_n=int(tr_cyc_n),
            trace_bdry_pow_n=int(tr_bdry_n),
            audit_diag_support_equals_cyc=bool(audit_diag),
            audit_trace_at_n_ok=bool(audit_trace),
            bdry_words=list(bdry),
            cyc_words_head=list(cyc[: min(12, len(cyc))]),
        )

        # Write JSON + adjacency CSV
        (run.run_dir / "result.json").write_text(
            json.dumps(asdict(res), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with open(run.run_dir / "adjacency.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["i", "word", "out_degree", "neighbors"])
            for i, word in enumerate(words):
                nbrs = [int(j) for j in np.nonzero(B[i, :])[0].tolist()]
                nbr_words = [words[j] for j in nbrs]
                w.writerow([i, word, len(nbrs), " ".join(nbr_words)])

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Always emit TeX fragment deterministically from cached JSON.
    payload = json.loads((run.run_dir / "result.json").read_text(encoding="utf-8"))
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    out_tex = gen / "eq_x6_cyc_bdry_pi_channel_projection.tex"

    n = int(payload["n"])
    X = int(payload["X_size"])
    Xc = int(payload["X_cyc_size"])
    Xb = int(payload["X_bdry_size"])
    rho_full = float(payload["rho_full"])
    rho_cyc = float(payload["rho_cyc"])
    rho_bdry = float(payload["rho_bdry"])
    bdry_words = payload.get("bdry_words", [])
    ok_diag = bool(payload.get("audit_diag_support_equals_cyc", False))
    ok_trace_n = bool(payload.get("audit_trace_at_n_ok", False))
    tr_n = int(payload.get("trace_B_pow_n", 0))

    def _fmt(x: float, nd: int = 12) -> str:
        return f"{float(x):.{int(nd)}f}"

    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_x6_cyc_bdry_pi_channel_projection.py")
    lines.append("\\[")
    lines.append("\\begin{aligned}")
    lines.append(
        f"|X_{{{n}}}|&={X},\\qquad |X_{{{n}}}^{{\\mathrm{{cyc}}}}|={Xc},\\qquad |X_{{{n}}}^{{\\mathrm{{bdry}}}}|={Xb},\\\\"
    )
    if n == 6 and isinstance(bdry_words, list) and bdry_words:
        bd = ",\\ ".join([f"\\texttt{{{w}}}" for w in bdry_words])
        lines.append(f"X_6^{{\\mathrm{{bdry}}}}&=\\{{{bd}\\}},\\\\")
    lines.append(
        f"\\rho(B_{{{n}}})&\\approx {_fmt(rho_full, 12)},\\qquad \\rho(P_{{\\mathrm{{cyc}}}}B_{{{n}}}P_{{\\mathrm{{cyc}}}})\\approx {_fmt(rho_cyc, 12)},\\qquad \\rho(P_{{\\mathrm{{bdry}}}}B_{{{n}}}P_{{\\mathrm{{bdry}}}})\\approx {_fmt(rho_bdry, 12)},\\\\"
    )
    lines.append(
        "\\mathrm{Audit:}\\ "
        + (f"\\mathrm{{Tr}}(B^{{{n}}})={tr_n}=|X_{{{n}}}^{{\\mathrm{{cyc}}}}|\\ \\mathrm{{OK}}" if ok_trace_n else f"\\mathrm{{Tr}}(B^{{{n}}})\\ \\mathrm{{FAIL}}")
        + ",\\ "
        + ("\\mathrm{supp}\\,\\mathrm{diag}(B^n)=X_n^{\\mathrm{cyc}}\\ \\mathrm{OK}" if ok_diag else "\\mathrm{supp}\\,\\mathrm{diag}(B^n)\\ \\mathrm{FAIL}")
        + "."
    )
    lines.append("\\end{aligned}")
    lines.append("\\]")
    lines.append("")
    out_tex.write_text("\n".join(lines), encoding="utf-8")

    print(f"[x6-cyc-bdry] wrote {out_tex}", flush=True)
    print(f"[x6-cyc-bdry] artifacts: {run.run_dir}", flush=True)


if __name__ == "__main__":
    main()

