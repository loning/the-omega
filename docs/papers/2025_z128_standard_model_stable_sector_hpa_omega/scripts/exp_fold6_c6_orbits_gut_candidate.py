#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Window-6: C6 rotation orbits on X6^{cyc} and Fold_m uplift sheet diagnostics.

This script is designed to make two "internal" structures auditable from the
finite definitions already present in the 2025 window-6 minimal model:

1) The cyclic sector X6^{cyc} (18 words) is rotation-invariant under the C6
   position shift. We compute its orbit decomposition and verify the rigid
   1⊕2⊕3⊕6⊕6 split (with explicit orbit contents).

2) The Fold_m truncation map (Zeckendorf digits) induces finite preimage fibers
   and "uplift deltas" δ = N - V_m(w). We print the boundary-sector fibers and
   δ-sets at m=6,7,8 to test whether the m=6 two-sheet phenomenon persists.

Only the Python standard library plus local scripts in this directory are used.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import DefaultDict, Dict, Iterable, List, Sequence, Tuple

import exp_foldm_stats as foldm_stats
import exp_xm_enumeration as xm_enum


def rotate_left(w: str, k: int = 1) -> str:
    """Cyclic left rotation by k positions."""
    if not w:
        return w
    k %= len(w)
    return w[k:] + w[:k]


def c_orbit(w: str) -> List[str]:
    """Return the full C_m orbit of w (with m=len(w)), unique and sorted."""
    m = len(w)
    orb = {rotate_left(w, k) for k in range(m)}
    return sorted(orb)


def is_cyclic_pi_sector_word(w: str) -> bool:
    """
    Pi-channel 'cyclic' sector: w1*wm = 0  (equivalently: not (w1=wm=1)).

    This is the maximal subset of X_m that is invariant under cyclic rotation.
    """
    return not (w[0] == "1" and w[-1] == "1")


def fib_weights_f2_to_f_mplus1(m: int) -> List[int]:
    """
    Return weights [F2, F3, ..., F_{m+1}] with F1=F2=1.

    For m=6 this is [1, 2, 3, 5, 8, 13].
    """
    if m <= 0:
        raise ValueError("m must be positive.")
    weights = [1, 2]
    while len(weights) < m:
        weights.append(weights[-1] + weights[-2])
    return weights[:m]


def zeckendorf_value(w: str) -> int:
    weights = fib_weights_f2_to_f_mplus1(len(w))
    return sum(int(b) * weights[i] for i, b in enumerate(w))


def preimage_map(m: int) -> Dict[str, List[int]]:
    """
    Compute the full Fold_m^{-1}(w) lists by brute force enumeration of N.
    """
    pre: DefaultDict[str, List[int]] = defaultdict(list)
    for n in range(1 << m):
        w = foldm_stats.foldm(n, m)
        pre[w].append(n)
    return dict(pre)


def delta_set(pre: Dict[str, List[int]], w: str) -> List[int]:
    v = zeckendorf_value(w)
    return sorted({n - v for n in pre[w]})


def _hamming_weight(w: str) -> int:
    return w.count("1")


def summarize_orbits_x6() -> None:
    X6 = sorted(xm_enum.all_xm(6))
    bdry = [w for w in X6 if xm_enum.is_boundary_word(w)]
    cyc = [w for w in X6 if is_cyclic_pi_sector_word(w)]
    assert len(X6) == 21, f"expected |X6|=21, got {len(X6)}"
    assert len(bdry) == 3, f"expected |X6^bdry|=3, got {len(bdry)}"
    assert len(cyc) == 18, f"expected |X6^cyc|=18, got {len(cyc)}"

    # Orbit decomposition on X6^{cyc}.
    remaining = set(cyc)
    orbits: List[List[str]] = []
    while remaining:
        w = min(remaining)
        orb = c_orbit(w)
        # Rotation invariance should hold inside the pi-cyclic sector.
        if not set(orb).issubset(set(cyc)):
            bad = sorted(set(orb) - set(cyc))
            raise AssertionError(f"orbit left X6^cyc. seed={w}, outside={bad}")
        orbits.append(orb)
        remaining -= set(orb)

    orbits.sort(key=lambda o: (len(o), o[0]))

    print("X6^bdry =", bdry)
    print("\nC6 orbit decomposition on X6^cyc (sorted by size):")
    for orb in orbits:
        print(f"  size {len(orb)} :", "{" + ", ".join(orb) + "}")
    print("\nOrbit sizes:", [len(o) for o in orbits], "(sum =", sum(len(o) for o in orbits), ")")

    # Expected rigid split stated in the user's GUT-oriented note.
    expected_orbits = [
        ["000000"],
        ["010101", "101010"],
        ["001001", "010010", "100100"],
        ["000001", "000010", "000100", "001000", "010000", "100000"],
        ["000101", "001010", "010001", "010100", "100010", "101000"],
    ]
    expected_orbits = [sorted(o) for o in expected_orbits]
    expected_orbits.sort(key=lambda o: (len(o), o[0]))

    if [sorted(o) for o in orbits] != expected_orbits:
        print("\n[WARN] Orbit contents differed from the expected five orbits.")
        print("Expected:", expected_orbits)
        print("Got     :", [sorted(o) for o in orbits])
    else:
        print("\n[OK] Orbit split matches 1⊕2⊕3⊕6⊕6 with the expected orbit contents.")

    # --- A minimal "Pati–Salam-style" candidate dictionary (vector-space level) ---
    # This is intentionally labeled as a *candidate* mapping: orbit sizes alone
    # do not define a Lie bracket. The purpose is to freeze the orbit classes
    # into a reproducible lookup that downstream invariants can be compared
    # against (degeneracy, uplift deltas, spectral/trace proxies, etc.).
    pre6 = preimage_map(6)

    orbit_label: Dict[str, str] = {}
    orbit_words_by_label: Dict[str, List[str]] = {}
    for orb in orbits:
        rep = orb[0]
        if len(orb) == 1:
            lab = "cyc_orbit_1__u1_candidate"
        elif len(orb) == 2:
            lab = "cyc_orbit_2__su3_cartan_candidate"
        elif len(orb) == 3:
            lab = "cyc_orbit_3__su2L_candidate"
        elif len(orb) == 6 and _hamming_weight(rep) == 1:
            lab = "cyc_orbit_6a__su3_step_candidate"
        elif len(orb) == 6 and _hamming_weight(rep) == 2:
            lab = "cyc_orbit_6b__su4_bridge_candidate"
        else:
            lab = f"cyc_orbit_{len(orb)}__unlabeled"

        for w in orb:
            orbit_label[w] = lab
        orbit_words_by_label[lab] = list(orb)

    for w in bdry:
        orbit_label[w] = "bdry__su2R_candidate"
    orbit_words_by_label["bdry__su2R_candidate"] = list(bdry)

    su4_words = (
        orbit_words_by_label["cyc_orbit_1__u1_candidate"]
        + orbit_words_by_label["cyc_orbit_2__su3_cartan_candidate"]
        + orbit_words_by_label["cyc_orbit_6a__su3_step_candidate"]
        + orbit_words_by_label["cyc_orbit_6b__su4_bridge_candidate"]
    )
    su2L_words = orbit_words_by_label["cyc_orbit_3__su2L_candidate"]
    su2R_words = orbit_words_by_label["bdry__su2R_candidate"]

    print("\n--- Candidate GUT partition (C6-orbit dictionary; vector-space level) ---")
    print("su4_candidate (15) =", su4_words)
    print("su2L_candidate (3) =", su2L_words)
    print("su2R_candidate (3) =", su2R_words)

    # --- Executable proxy: degeneracy/uplift-cardinality summaries per class ---
    def class_stats(words: Sequence[str]) -> Tuple[Dict[int, int], float, float]:
        gs = [len(pre6[w]) for w in words]
        hist = dict(sorted(Counter(gs).items()))
        mean_g = sum(gs) / len(gs) if gs else float("nan")
        mean_log_g = sum(math.log(x) for x in gs) / len(gs) if gs else float("nan")
        return hist, mean_g, mean_log_g

    print("\n--- Proxy summaries at m=6 (degeneracy/uplift-cardinality) ---")
    for lab in sorted(orbit_words_by_label.keys()):
        words = orbit_words_by_label[lab]
        if lab == "bdry__su2R_candidate":
            # Keep boundary last for readability.
            continue
        hist, mean_g, mean_log_g = class_stats(words)
        print(f"{lab}: size={len(words):>2}  g_hist={hist}  mean_g={mean_g:.3f}  mean_log_g={mean_log_g:.3f}")
    # boundary class
    hist, mean_g, mean_log_g = class_stats(orbit_words_by_label["bdry__su2R_candidate"])
    print(f"bdry__su2R_candidate: size={len(su2R_words):>2}  g_hist={hist}  mean_g={mean_g:.3f}  mean_log_g={mean_log_g:.3f}")

    print("\nWord -> class label (m=6):")
    for w in X6:
        g = len(pre6[w])
        print(f"  {w}  g={g}  class={orbit_label[w]}")


def summarize_uplift_sheets(m_list: Sequence[int] = (6, 7, 8)) -> None:
    print("\n--- Fold_m boundary-sector uplift diagnostics ---")
    for m in m_list:
        Xm = sorted(xm_enum.all_xm(m))
        pre = preimage_map(m)
        bdry = [w for w in Xm if xm_enum.is_boundary_word(w)]
        last1 = [w for w in Xm if w[-1] == "1"]

        # Boundary summary histograms.
        bdry_g_hist = Counter(len(pre[w]) for w in bdry)
        bdry_delta_card_hist = Counter(len(delta_set(pre, w)) for w in bdry)

        print(f"\nm={m}: |X_m|={len(Xm)}, |X_m^bdry|={len(bdry)}, |{{w: w_m=1}}|={len(last1)}")
        print("  boundary preimage-size histogram:", dict(sorted(bdry_g_hist.items())))
        print("  boundary |δ-set| histogram      :", dict(sorted(bdry_delta_card_hist.items())))

        # Print each boundary word with its δ-set.
        for w in bdry:
            v = zeckendorf_value(w)
            ns = pre[w]
            deltas = delta_set(pre, w)
            d_str = "{" + ", ".join(str(x) for x in deltas) + "}"
            print(f"  bdry {w}  V={v:>3}  pre={ns}  δ={d_str}")

        # Check the "two-sheet" phenomenon for words with last digit 1.
        last1_delta_card_hist = Counter(len(delta_set(pre, w)) for w in last1)
        print("  last-bit=1 |δ-set| histogram    :", dict(sorted(last1_delta_card_hist.items())))


def main() -> None:
    summarize_orbits_x6()
    summarize_uplift_sheets(m_list=(6, 7, 8))


if __name__ == "__main__":
    main()

