#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-checks for the independent ontic-layer implementation (src project)."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Dict, Tuple

from .ontic_system import OnticZeckendorfSystem


def _all_no_adjacent_words(L: int) -> list[int]:
    out: list[int] = []
    for x in range(1 << int(L)):
        if (x & (x << 1)) == 0:
            out.append(int(x))
    return out


def _check_enc_rec(m: int) -> None:
    sys = OnticZeckendorfSystem(window_length=m)
    n = 1 << m
    print(f"[zeckendorf_ontic:selfcheck] check enc/rec m={m} n_micro={n}", flush=True)

    pairs_to_N: Dict[Tuple[int, int], int] = {}
    for i in range(n):
        if i % 512 == 0 and i > 0:
            print(f"[zeckendorf_ontic:selfcheck]  progress m={m}: N={i}/{n}", flush=True)
        p = sys.enc(i)
        if not sys.ok(p.macro_word, p.tail_word):
            raise SystemExit(f"FAIL ok(enc(N)) m={m} N={i}")
        key = (p.macro_word, p.tail_word)
        if key in pairs_to_N and pairs_to_N[key] != i:
            raise SystemExit(f"FAIL enc not injective m={m} pair={key} N={pairs_to_N[key]} vs {i}")
        pairs_to_N[key] = i

    for (macro_word, tail_word), N in pairs_to_N.items():
        Nr = sys.rec(macro_word, tail_word)
        if Nr is None or int(Nr) != int(N):
            raise SystemExit(f"FAIL rec(enc(N)) m={m} pair={(macro_word,tail_word)} expected {N} got {Nr}")

    print(f"[zeckendorf_ontic:selfcheck] OK m={m} |A_m|={len(pairs_to_N)}", flush=True)


def _check_m6_hist() -> None:
    sys = OnticZeckendorfSystem(window_length=6)
    ys = _all_no_adjacent_words(6)
    if len(ys) != 21:
        raise SystemExit(f"FAIL m=6: expected |Y_m|=21, got {len(ys)}")

    hist = Counter(sys.fiber_size(macro_word) for macro_word in ys)
    print(f"[zeckendorf_ontic:selfcheck] m=6 fiber histogram: {dict(sorted(hist.items()))}", flush=True)
    expected = {2: 8, 3: 4, 4: 9}
    if dict(hist) != expected:
        raise SystemExit(f"FAIL m=6 histogram mismatch expected {expected} got {dict(hist)}")
    print("[zeckendorf_ontic:selfcheck] OK m=6 histogram matches {2:8,3:4,4:9}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m_max", type=int, default=10)
    args = ap.parse_args()

    m_max = int(args.m_max)
    for m in range(1, m_max + 1):
        _check_enc_rec(m)
    _check_m6_hist()
    print("[zeckendorf_ontic:selfcheck] ALL OK", flush=True)


if __name__ == "__main__":
    main()

