#!/usr/bin/env python3
"""Export finite rule tables induced by Fold6 + 3-bit overlap.

Outputs (CSV):
  - stable_words_x6.csv
  - interface_rule_5x5.csv
  - pair_rule_21x21.csv

Definitions:
  - X6 is the 21-word admissible set (no adjacent 1s) realized as Fold6 image.
  - 3-bit interface alphabet A3 has size 5: 000,001,010,100,101.
  - 5x5 interface table: (suffix3, prefix3) -> (micro6, Fold6(micro6), uplift).
  - 21x21 pair-rule: (wL, wR) -> (Fold6(suffix3(wL)+prefix3(wR)), uplift).
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List, Tuple

import numpy as np

from hpa_ca_lossless import UPLIFT_TO_CODE, fold6_kernel


def bits_to_str(bits: np.ndarray) -> str:
    return "".join(str(int(b)) for b in bits.tolist())


def str_to_bits(s: str) -> np.ndarray:
    return np.array([0 if ch == "0" else 1 for ch in s.strip()], dtype=np.uint8)


def is_admissible_no11(word: str) -> bool:
    return "11" not in word


def stable_words_x6() -> List[str]:
    # Enumerate all admissible 6-bit words; this is small and explicit.
    words = []
    for i in range(64):
        w = format(i, "06b")
        if is_admissible_no11(w):
            words.append(w)
    # For m=6, admissible count is 21.
    words = sorted(words)
    if len(words) != 21:
        raise RuntimeError(f"Expected 21 admissible words, got {len(words)}")
    return words


def interface_alphabet_3() -> List[str]:
    # All 3-bit words with no adjacent 1s: 000,001,010,100,101
    A = []
    for i in range(8):
        w = format(i, "03b")
        if "11" not in w:
            A.append(w)
    A = sorted(A)
    if len(A) != 5:
        raise RuntimeError(f"Expected 5 admissible 3-bit words, got {len(A)}")
    return A


def export_stable_words(words: List[str], outdir: str) -> str:
    path = os.path.join(outdir, "stable_words_x6.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "word"])
        for i, word in enumerate(words):
            w.writerow([i, word])
    return path


def export_interface_5x5(outdir: str) -> str:
    A3 = interface_alphabet_3()
    path = os.path.join(outdir, "interface_rule_5x5.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "left_suffix3",
                "right_prefix3",
                "micro6",
                "fold6_word",
                "uplift_value",
                "uplift_code",
            ]
        )
        for a in A3:
            for b in A3:
                micro = a + b
                bits = str_to_bits(micro)
                out_bits, uplift = fold6_kernel(bits)
                out_word = bits_to_str(out_bits)
                w.writerow([a, b, micro, out_word, uplift, UPLIFT_TO_CODE[uplift]])
    return path


def export_pair_rule_21x21(words: List[str], outdir: str) -> str:
    idx: Dict[str, int] = {w: i for i, w in enumerate(words)}
    path = os.path.join(outdir, "pair_rule_21x21.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "left_idx",
                "left_word",
                "right_idx",
                "right_word",
                "micro6",
                "out_idx",
                "out_word",
                "uplift_value",
                "uplift_code",
            ]
        )
        for wl in words:
            suf = wl[3:6]
            for wr in words:
                pre = wr[0:3]
                micro = suf + pre
                bits = str_to_bits(micro)
                out_bits, uplift = fold6_kernel(bits)
                out_word = bits_to_str(out_bits)
                w.writerow(
                    [
                        idx[wl],
                        wl,
                        idx[wr],
                        wr,
                        micro,
                        idx[out_word],
                        out_word,
                        uplift,
                        UPLIFT_TO_CODE[uplift],
                    ]
                )
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=str, default="out_rules_fold6", help="output directory")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    words = stable_words_x6()
    p_words = export_stable_words(words, args.outdir)
    p_if = export_interface_5x5(args.outdir)
    p_pair = export_pair_rule_21x21(words, args.outdir)

    print("Wrote:")
    print(f"  - {p_words}")
    print(f"  - {p_if}")
    print(f"  - {p_pair}")


if __name__ == "__main__":
    main()

