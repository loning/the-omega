# -*- coding: utf-8 -*-
"""
Monte Carlo null: does reverse compilation select mu* just by chance?

We randomize the genetic code table while preserving amino-acid / stop degeneracies:
  - keep the multiset of 64 labels (20 AA + Stop with their codon counts),
  - randomly permute these labels over the 64 codons.

For each randomized table, define the control set:
  K := {the unique Met codon} ∪ {the three Stop codons}.

Then repeat the Experiment-1 reverse-compilation scan:
  - for each 2-bit encoding mu (24 total), compute the boundary-hit score
      S_mu(K) = sum_{c in K} 1{ Fold6(N_mu(c)) is a boundary word },
  - record the maximizing encoding(s).

We also test the start/stop boundary-homology condition under mu*:
  the Met codon and at least one Stop codon land on the SAME boundary word.

Outputs (written under sections/generated/):
  - random_code_monte_carlo_summary.tex  (LaTeX-ready paragraph with p-value etc.)
  - random_code_monte_carlo_hist.png     (histogram / bar chart with real-code marker)

Unlike most other scripts in this paper, this experiment uses numpy/matplotlib
for performance (n up to 1e6) and plotting.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, all_encodings, codon_bits, fold6

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 2


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Monte Carlo null over random genetic code tables (degeneracy-preserving).")
    p.add_argument("--n", type=int, default=1_000_000, help="Number of random tables to sample.")
    p.add_argument("--seed", type=int, default=0, help="RNG seed.")
    p.add_argument("--chunk", type=int, default=50_000, help="Chunk size for vectorized sampling.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def _labels_and_groups() -> tuple[list[str], list[str], dict[str, int], np.ndarray, list[np.ndarray]]:
    """
    Return:
      - codons (stable order, length 64)
      - labels (AA/Stop names, length 21)
      - label_to_idx (label -> int)
      - base_labels_idx: shape (64,) label indices for the real code
      - groups: list of position arrays, one per Fold6 word (21 groups), with group sizes in {2,3,4}
    """
    codons = sorted(GENETIC_CODE.keys())
    if len(codons) != 64:
        raise AssertionError("Expected 64 codons.")

    # Real genetic code labels (AA/Stop) in codon order.
    aa_list = [GENETIC_CODE[c] for c in codons]
    labels = sorted(set(aa_list), key=lambda x: (x == "Stop", x))
    if len(labels) != 21:
        raise AssertionError("Expected 21 labels (20 AA + Stop).")
    label_to_idx = {lab: i for i, lab in enumerate(labels)}

    base_labels_idx = np.array([label_to_idx[a] for a in aa_list], dtype=np.uint8)

    # Fold6 groups under mu* in the SAME codon order.
    word_to_pos: dict[str, list[int]] = {}
    for i, codon in enumerate(codons):
        bits = codon_bits(codon, MU_STAR)
        n = int(bits, 2)
        w = fold6(n)
        word_to_pos.setdefault(w, []).append(i)

    # Deterministic group order.
    words = sorted(word_to_pos.keys())
    if len(words) != 21:
        raise AssertionError(f"Expected 21 Fold6 words, got {len(words)}")

    groups: list[np.ndarray] = []
    total = 0
    for w in words:
        pos = np.array(word_to_pos[w], dtype=np.int64)
        if pos.size not in (2, 3, 4):
            raise AssertionError(f"Unexpected Fold6 preimage size {pos.size} for word {w}")
        groups.append(pos)
        total += int(pos.size)
    if total != 64:
        raise AssertionError("Group sizes did not sum to 64.")

    return codons, labels, label_to_idx, base_labels_idx, groups


def _encode_to_str(mu: dict[str, str]) -> str:
    return f"A={mu['A']}, C={mu['C']}, G={mu['G']}, U={mu['U']}"


def _precompute_boundary_arrays(codons: list[str]) -> tuple[list[dict[str, str]], int, np.ndarray, np.ndarray]:
    """
    Precompute, for each encoding mu (24 total) and each codon position (64):
      - boundary_hit[mu_idx, codon_pos] in {0,1}
      - boundary_word_id[mu_idx, codon_pos] in {-1,0,1,2} for the three boundary words
    Also return the mu list and the index of mu* within it.
    """
    mus = all_encodings()
    if len(mus) != 24:
        raise AssertionError("Expected 24 encodings.")

    mu_star_idx = None
    for i, mu in enumerate(mus):
        if mu == MU_STAR:
            mu_star_idx = int(i)
            break
    if mu_star_idx is None:
        raise AssertionError("Failed to locate mu* among the 24 encodings.")

    bw = sorted(BOUNDARY_WORDS)
    if len(bw) != 3:
        raise AssertionError("Expected 3 boundary words.")
    bw_to_id = {w: i for i, w in enumerate(bw)}

    boundary_hit = np.zeros((24, 64), dtype=np.uint8)
    boundary_word_id = np.full((24, 64), -1, dtype=np.int8)
    for mi, mu in enumerate(mus):
        for ci, codon in enumerate(codons):
            bits = codon_bits(codon, mu)
            n = int(bits, 2)
            w = fold6(n)
            if w in BOUNDARY_WORDS:
                boundary_hit[mi, ci] = 1
                boundary_word_id[mi, ci] = int(bw_to_id[w])
    return mus, mu_star_idx, boundary_hit, boundary_word_id


def main() -> None:
    args = parse_args()
    n = int(args.n)
    if n <= 0:
        raise SystemExit("--n must be positive")

    out_tex = generated_dir() / "random_code_monte_carlo_summary.tex"
    out_png = generated_dir() / "random_code_monte_carlo_hist.png"

    cache_file = data_root() / "_cache" / f"random_code_monte_carlo_v{int(ANALYSIS_VERSION)}.json"
    cache_key = {
        "analysis": "random_code_monte_carlo",
        "analysis_version": int(ANALYSIS_VERSION),
        "mu_star": MU_STAR,
        "n": int(n),
        "seed": int(args.seed),
        "chunk": int(args.chunk),
        "outputs": [str(out_tex), str(out_png)],
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and out_tex.exists() and out_png.exists() and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {cache_file}")
        print("Wrote:", out_tex)
        print("Wrote:", out_png)
        return

    codons, labels, label_to_idx, base_labels_idx, groups = _labels_and_groups()
    _ = groups  # groups are not used by this experiment (kept for compatibility with the shared loader)
    if "Met" not in label_to_idx or "Stop" not in label_to_idx:
        raise AssertionError("Expected Met and Stop labels to exist.")
    met_idx = int(label_to_idx["Met"])
    stop_idx = int(label_to_idx["Stop"])

    mus, mu_star_idx, boundary_hit, boundary_word_id = _precompute_boundary_arrays(codons)
    # The paper's concrete start/stop symmetry is tied to the specific boundary word 100001 (the 14/48 split under mu*).
    target_boundary_word = "100001"
    bdry_words_sorted = sorted(BOUNDARY_WORDS)
    if target_boundary_word not in bdry_words_sorted:
        raise AssertionError("Expected boundary word 100001 to exist.")
    target_bdry_id = int(bdry_words_sorted.index(target_boundary_word))

    # Real-code control set (derived from the real genetic code table): Met codon + three Stop codons.
    met_pos_real = int(np.nonzero(base_labels_idx == met_idx)[0][0])
    stop_pos_real = np.nonzero(base_labels_idx == stop_idx)[0].astype(np.int64)
    if stop_pos_real.size != 3:
        raise AssertionError("Expected exactly 3 stop codons.")
    # For each encoding: S(mu) = boundary hits over K.
    s_real = boundary_hit[:, met_pos_real] + boundary_hit[:, stop_pos_real].sum(axis=1)
    smax_real = int(s_real.max())
    m_real = int(np.count_nonzero(s_real == smax_real))
    best_real = int(np.argmax(s_real))
    mu_star_unique_real = (best_real == int(mu_star_idx)) and (m_real == 1)
    # Start/stop boundary homology under mu*: Met and a Stop share the specific boundary word 100001.
    w_start_real = int(boundary_word_id[int(mu_star_idx), met_pos_real])
    w_stop_real = boundary_word_id[int(mu_star_idx), stop_pos_real]
    hom_real = (w_start_real == target_bdry_id) and bool(np.any(w_stop_real == target_bdry_id))
    score_real = int(mu_star_unique_real) + int(mu_star_unique_real and hom_real)
    print("Real-code control set:")
    print(f"  S_max={smax_real}, argmax multiplicity M={m_real}, mu* unique argmax={mu_star_unique_real}")
    print(f"  start/stop boundary homology on {target_boundary_word} under mu*: {hom_real}")
    print(f"  symmetry score (0/1/2) = {score_real}")

    rng = np.random.default_rng(int(args.seed))
    chunk = int(args.chunk)
    if chunk <= 0:
        raise SystemExit("--chunk must be positive")
    if chunk > n:
        chunk = n

    # Monte Carlo tallies (avoid storing per-sample arrays; we only need histograms / counts).
    score_counts = np.zeros(3, dtype=np.int64)  # 0/1/2
    smax_counts = np.zeros(5, dtype=np.int64)  # S_max in {0,1,2,3,4}
    mu_star_unique = 0
    mu_star_unique_and_hom = 0

    done = 0
    while done < n:
        m = min(chunk, n - done)

        # Random permutation of the multiset of labels for each row via random-key argsort.
        keys = rng.random((m, 64), dtype=np.float32)
        perm = np.argsort(keys, axis=1)
        assign = base_labels_idx[perm]  # (m,64) uint8

        # Identify the unique Met position and the three Stop positions per row.
        met_rows, met_cols = np.nonzero(assign == met_idx)
        if met_cols.size != m:
            raise AssertionError("Unexpected Met count per row (expected exactly 1).")
        # met_cols are in row-major order; safe to use directly.

        stop_rows, stop_cols = np.nonzero(assign == stop_idx)
        if stop_cols.size != m * 3:
            raise AssertionError("Unexpected Stop count per row (expected exactly 3).")
        stop_cols = stop_cols.reshape(m, 3)

        # Boundary-hit score S(mu) for each encoding and each row.
        b_start = boundary_hit[:, met_cols]  # (24,m)
        b_stops = boundary_hit[:, stop_cols]  # (24,m,3)
        S = b_start.astype(np.int16) + b_stops.sum(axis=2).astype(np.int16)  # (24,m)

        smax = S.max(axis=0).astype(np.int16)  # (m,)
        # histogram S_max
        smax_counts += np.bincount(smax, minlength=5).astype(np.int64)

        # argmax multiplicity
        m_mult = np.sum(S == smax, axis=0).astype(np.int16)  # (m,)
        best_idx = np.argmax(S, axis=0).astype(np.int16)  # (m,)

        is_mu_star_unique = (m_mult == 1) & (best_idx == int(mu_star_idx))
        mu_star_unique += int(np.count_nonzero(is_mu_star_unique))

        # start/stop boundary homology under mu* on the specific boundary word 100001
        # (only matters when mu* is the selected unique argmax).
        w_start = boundary_word_id[int(mu_star_idx), met_cols]  # (m,)
        w_stops = boundary_word_id[int(mu_star_idx), stop_cols]  # (m,3)
        hom = (w_start == target_bdry_id) & np.any(w_stops == target_bdry_id, axis=1)
        is_mu_star_unique_and_hom = is_mu_star_unique & hom
        mu_star_unique_and_hom += int(np.count_nonzero(is_mu_star_unique_and_hom))

        # Symmetry score (0/1/2).
        score = is_mu_star_unique.astype(np.int16) + is_mu_star_unique_and_hom.astype(np.int16)
        score_counts += np.bincount(score, minlength=3).astype(np.int64)

        done += m
        if done % 200_000 == 0 or done == n:
            print(f"  sampled {done}/{n}...")

    p_mu_star_unique = mu_star_unique / float(n)
    p_mu_star_unique_hom = mu_star_unique_and_hom / float(n)

    # LaTeX summary fragment.
    # The p-value reported is the probability that a random code achieves the FULL symmetry score=2,
    # including the concrete 100001 boundary-word homology used in the paper (the 14/48 split under mu*).
    p_line = f"$p={p_mu_star_unique_hom:.6g}$"
    if mu_star_unique_and_hom == 0:
        p_line = f"$p< {1.0/float(n):.6g}$ (0/{n} samples)"

    smax_hist_tex = ",\\ ".join(f"{i}:{int(smax_counts[i])}" for i in range(5))
    score_hist_tex = ",\\ ".join(f"{i}:{int(score_counts[i])}" for i in range(3))

    tex = (
        "Degeneracy-preserving Monte Carlo null over random genetic codes "
        f"($n={n:,}$ random tables; fixed $\\mathrm{{Fold}}_6$; scan over $24$ encodings). "
        "For each random table we define $\\mathcal{K}=\\{\\mathrm{Met}\\}\\cup\\{\\mathrm{Stop}\\}$ "
        "(the unique Met codon plus the three Stop codons), and compute the boundary-hit objective "
        "$S_{\\mathcal{K}}(\\mu)=\\sum_{c\\in\\mathcal{K}}\\mathbf{1}\\{w_\\mu(c)\\in X_6^{\\mathrm{bdry}}\\}$, "
        "selecting the maximizing encoding(s). "
        f"For the real genetic code, $S_\\max={smax_real}$ with argmax multiplicity $M={m_real}$ and unique maximizer $\\mu^\\ast$ "
        f"(start/stop boundary homology on \\texttt{{{target_boundary_word}}} under $\\mu^\\ast$: {('yes' if hom_real else 'no')}). "
        f"Across the random tables, the $S_\\max$ histogram is $\\{{{smax_hist_tex}\\}}$ and the symmetry-score histogram is "
        f"$\\{{{score_hist_tex}\\}}$, where score $0$ means $\\mu^\\ast$ is not the unique maximizer, score $1$ means $\\mu^\\ast$ is the unique maximizer, "
        "and score $2$ means additionally that the Met codon and a Stop codon share the same \\emph{specific} boundary word "
        f"\\texttt{{{target_boundary_word}}} under $\\mu^\\ast$. "
        f"The probability of reproducing the full real-code pattern (score $2$) under this null is {p_line}."
        "\n"
    )
    write_text_atomic(out_tex, tex)

    # Plot: bar chart for the 0/1/2 symmetry score.
    plt.figure(figsize=(6.8, 3.4), dpi=180)
    xs = np.array([0, 1, 2], dtype=np.int64)
    ys = score_counts.astype(np.float64)
    plt.bar(xs, ys, color="#4C72B0", alpha=0.85, edgecolor="white", linewidth=0.6)
    plt.xticks(xs, ["0", "1", "2"])
    plt.xlabel("symmetry score")
    plt.ylabel("count (out of n)")
    plt.title("Random genetic-code null (degeneracy-preserving)")
    # Mark the real code score.
    plt.axvline(score_real, color="#C44E52", linewidth=2.0, label=f"real code score = {score_real}")
    plt.legend(frameon=False, loc="upper right")
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png)
    plt.close()

    # Cache marker.
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        cache_file,
        {
            "ok": True,
            "n": int(n),
            "seed": int(args.seed),
            "chunk": int(args.chunk),
            "smax_counts": {str(i): int(smax_counts[i]) for i in range(5)},
            "score_counts": {str(i): int(score_counts[i]) for i in range(3)},
            "mu_star_unique": int(mu_star_unique),
            "mu_star_unique_and_hom": int(mu_star_unique_and_hom),
            "p_mu_star_unique": float(p_mu_star_unique),
            "p_mu_star_unique_hom": float(p_mu_star_unique_hom),
            "real": {
                "smax": int(smax_real),
                "M": int(m_real),
                "mu_star_unique": bool(mu_star_unique_real),
                "homology_mu_star": bool(hom_real),
                "score": int(score_real),
            },
        },
    )
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote:", out_tex)
    print("Wrote:", out_png)


if __name__ == "__main__":
    main()

