# -*- coding: utf-8 -*-
"""
BH5 audit: CAP-select the minimal repetition-code redundancy r* needed for target recovery under record noise.

We treat the repetition family r in {1,3,5,7} as a finite candidate set and define a protocol-level CAP rule:
  choose the smallest r achieving ok_rate >= ok_threshold for a fixed noise budget p
  (and fixed interface perturbation model: corruption in {"safe","full"}).

Outputs:
  - sections/generated/bh_page_record_noise_ecc_cap_select_rows.tex
  - sections/generated/bh_page_record_noise_ecc_cap_select_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import Dict, List

from common_paths import generated_dir
from common_progress import ProgressEvery
from common_tex import write_lines

from exp_bh_page_surrogate_record_noise_ecc_audit import _run_trials


def _cap_select_r_star(
    *,
    m: int,
    mode: str,
    corr: str,
    p: float,
    rs: List[int],
    trials: int,
    seed: int,
    ok_threshold: float,
) -> Dict[str, str]:
    best = None
    r_star = None
    for r in sorted(int(x) for x in rs):
        out = _run_trials(m=m, mode=mode, corr=corr, p=p, r=r, trials=trials, seed=seed)
        best = out
        if float(out["ok_rate"]) >= float(ok_threshold):
            r_star = int(r)
            break

    if best is None:
        raise RuntimeError("empty rs candidate set")

    return {
        "m": str(int(m)),
        "mode": str(mode),
        "corr": str(corr),
        "p": f"{float(p):.3f}",
        "ok_threshold": f"{float(ok_threshold):.2f}",
        "r_star": str(r_star) if r_star is not None else "-",
        "ok_rate": str(best["ok_rate"]),
        "wrong_rate": str(best["wrong_rate"]),
        "exc_rate": str(best["exc_rate"]),
    }


def main() -> None:
    m_list = [6, 12]
    modes = ["cyclic_only", "avoid_delim_esc"]
    corrs = ["safe", "full"]
    ps = [0.0, 0.01, 0.02, 0.05, 0.10]
    rs = [1, 3, 5, 7]

    trials = 200
    seed0 = 20260112
    ok_threshold = 0.95

    rows: List[str] = []
    total = len(m_list) * len(modes) * len(corrs) * len(ps)
    prog = ProgressEvery(label="bh_record_noise_ecc_cap_select combos", total=total, interval_s=60.0)
    prog.start()
    k = 0
    for m in m_list:
        for mode in modes:
            for corr in corrs:
                for p in ps:
                    k += 1
                    prog.maybe(
                        k,
                        extra=f"m={m} mode={mode} corr={corr} p={float(p):.3f}",
                    )
                    out = _cap_select_r_star(
                        m=m,
                        mode=mode,
                        corr=corr,
                        p=float(p),
                        rs=rs,
                        trials=trials,
                        seed=seed0,
                        ok_threshold=ok_threshold,
                    )
                    rows.append(
                        " & ".join(
                            [
                                out["m"],
                                out["mode"],
                                out["corr"],
                                out["p"],
                                out["ok_threshold"],
                                out["r_star"],
                                out["ok_rate"],
                                out["wrong_rate"],
                                out["exc_rate"],
                            ]
                        )
                        + r" \\"
                    )
    prog.done(extra=f"rows={len(rows)}")
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_record_noise_ecc_cap_select_rows.tex", rows)

    summary = [
        r"\paragraph{CAP-selected redundancy for record-noise recovery (finite family).} \AuditTag "
        r"For each noise budget $p$ and corruption model, we CAP-select the minimal repetition factor "
        r"$r^\ast(p)\\in\\{1,3,5,7\\}$ that reaches a target exact-recovery rate (here: $\\ge 0.95$) under the "
        r"record-noise audit. This turns a robustness audit into a deterministic protocol choice over a finite family.",
    ]
    write_lines(generated_dir() / "bh_page_record_noise_ecc_cap_select_summary.tex", summary)

    print("Wrote sections/generated/bh_page_record_noise_ecc_cap_select_rows.tex")
    print("Wrote sections/generated/bh_page_record_noise_ecc_cap_select_summary.tex")


if __name__ == "__main__":
    main()

