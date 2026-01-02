# -*- coding: utf-8 -*-
"""
Enumerate admissible sets X_m (no consecutive ones) for multiple m values.

This script extends the m=6 enumeration to a small m-sweep used for
resolution-uplift audits and predictions.

We record:
  - |X_m|
  - |X_m^{cyc}| and |X_m^{bdry}| under the pi-channel wrap-around defect (w1=wm=1)

Outputs (LaTeX fragments):
  - sections/generated/xm_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from common_cache import CACHE_VERSION, cache_path, load_or_compute


def all_xm(m: int) -> List[str]:
    if m <= 0:
        raise ValueError("m must be positive.")
    key = cache_path(f"xm_words_m{m}_v{CACHE_VERSION}.pkl")

    def compute() -> List[str]:
        out: List[str] = []

        def rec(prefix: str, last: str) -> None:
            if len(prefix) == m:
                out.append(prefix)
                return
            # Always allowed to append 0.
            rec(prefix + "0", "0")
            # Append 1 only if last was not 1.
            if last != "1":
                rec(prefix + "1", "1")

        rec("", "0")
        return out

    return load_or_compute(key, compute)


def is_boundary_word(w: str) -> bool:
    return w[0] == "1" and w[-1] == "1"


def main() -> None:
    # Sweep values used in the paper (m-uplift at fixed n=3; also covers balanced m=2n for n=3..8).
    m_list = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    rows: List[str] = []
    for m in m_list:
        Xm = all_xm(m)
        total = len(Xm)
        bdry = sum(1 for w in Xm if is_boundary_word(w))
        cyc = total - bdry
        rows.append(f"{m} & {total} & {cyc} & {bdry} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "xm_sweep_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/xm_sweep_rows.tex")


if __name__ == "__main__":
    main()



