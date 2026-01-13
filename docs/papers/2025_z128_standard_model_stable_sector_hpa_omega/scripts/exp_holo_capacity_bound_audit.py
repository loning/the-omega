# -*- coding: utf-8 -*-
"""
Holographic capacity bound audit (deterministic, standard-library only).

Outputs (LaTeX fragments):
  - sections/generated/holo_capacity_bound_rows.tex
  - sections/generated/holo_capacity_bound_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Row:
    m: int
    n: int
    region_sites: int

    @property
    def i_prot_bits(self) -> int:
        return int(self.m) * int(self.region_sites)

    @property
    def log2_dim(self) -> int:
        # Under the tensor-product per-site convention d_site=2^m,
        # dim(H_R)=(2^m)^{|R|}=2^{m|R|}, hence log2 dim = m|R|.
        return int(self.m) * int(self.region_sites)


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "holo_capacity_bound_rows.tex"
    sum_path = out_dir / "holo_capacity_bound_summary.tex"

    # Anchor example used throughout the manuscript.
    m = 6
    n = 3
    # Representative region sizes (site counts) on the screen.
    region_sites_list = [1, 4, 16, 64]

    rows: List[str] = []
    for r in region_sites_list:
        row = Row(m=m, n=n, region_sites=int(r))
        rows.append(
            " & ".join(
                [
                    str(int(row.m)),
                    str(int(row.n)),
                    str(int(row.region_sites)),
                    str(int(row.i_prot_bits)),
                    str(int(row.log2_dim)),
                ]
            )
            + r" \\"
        )
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    summary = [
        r"\paragraph{Holographic capacity bound (finite-dimensional PT surrogate).} \AuditTag "
        + r"Under the per-site convention $d_{\mathrm{site}}(m)=2^m$ and tensor-product locality, "
        + r"a region $R$ of $|R|$ sites has $\log_2\dim(\mathcal{H}_R)=m|R|$, hence "
        + r"$S_{\partial}(R)\le \log_2\dim(\mathcal{H}_R)=I_{\mathrm{prot}}(m,n;R)=m|R|$.",
        r"\paragraph{Deterministic example set.} \AuditTag "
        + rf"Rows instantiate the anchor example (m={m}, n={n}) with region site counts {region_sites_list}.",
    ]
    write_lines(sum_path, summary)


if __name__ == "__main__":
    main()

