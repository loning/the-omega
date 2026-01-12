# -*- coding: utf-8 -*-
"""
BH5 audit: record-noise robustness for the queue-equivalent single-stream model.

Rationale:
  The most realistic perturbation at the interface layer is noise on the *external record*
  (measurement errors, coarse-graining mistakes, symbol corruption), not noise on hidden state.
  This script tests how robust exact recovery is under bounded symbol substitutions in the
  non-vacuum part of the record.

We sweep:
  - m in {6, 12}
  - mode in {cyclic_only, avoid_delim_esc}
  - corruption in {safe, full}
      safe: substitutions avoid the delimiter token to preserve tail detection (isolates decoding)
      full: substitutions can hit any symbol in X_m (includes false-delimiter events)
  - p in a small finite family

Outputs:
  - sections/generated/bh_page_record_noise_audit_rows.tex
  - sections/generated/bh_page_record_noise_audit_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines

import exp_black_hole_queue_equivalence as bhq


def _choose_indices(rng: random.Random, n: int, k: int) -> List[int]:
    if k <= 0:
        return []
    k = min(int(k), int(n))
    idx = list(range(n))
    rng.shuffle(idx)
    return sorted(idx[:k])


def _corrupt_record(
    rng: random.Random,
    Xm: List[str],
    record: List[str],
    nonvac_len: int,
    p: float,
    corruption: str,
    delim: str,
) -> List[str]:
    """
    Corrupt only the non-vacuum prefix of length nonvac_len by substituting k≈p*nonvac_len symbols.
    """
    if nonvac_len < 0 or nonvac_len > len(record):
        raise ValueError("invalid nonvac_len")
    if p < 0.0 or p > 1.0:
        raise ValueError("p must be in [0,1]")
    if corruption not in ("safe", "full"):
        raise ValueError("unknown corruption mode")

    out = list(record)
    k = int(round(float(p) * float(nonvac_len)))
    idxs = _choose_indices(rng, nonvac_len, k)
    for i in idxs:
        cur = out[i]
        # candidate alphabet for replacement
        if corruption == "safe":
            cand = [w for w in Xm if w != cur and w != delim]
        else:
            cand = [w for w in Xm if w != cur]
        if not cand:
            continue
        out[i] = cand[rng.randrange(0, len(cand))]
    return out


def _run_trials(m: int, mode: str, corruption: str, p: float, trials: int, seed: int) -> Dict[str, str]:
    rng = random.Random(int(seed))
    base_vacuum_mass = 64
    msg_text = "TICK-INFORMATION"

    bits = bhq._bits_from_ascii(msg_text)
    allowed, _info = bhq._allowed_set_by_mode(m, mode=mode)
    micro = bhq.bits_to_allowed_micro_indices(bits, allowed=allowed)

    _st, record, meta = bhq.forward_simulate_single_stream(
        base_vacuum_mass=base_vacuum_mass, m=m, message_micro=micro
    )

    Xm = bhq.all_xm(m)
    delim = str(meta["delim"])
    nonvac_len = int(meta["L"]) + int(meta["L"]) * int(meta["t"])
    # record includes vacuum tail; we keep tail intact to isolate non-vacuum corruption

    ok = 0
    wrong = 0
    exc = 0
    for t in range(int(trials)):
        rrng = random.Random(rng.randrange(0, 2**31 - 1))
        noisy = _corrupt_record(
            rng=rrng,
            Xm=Xm,
            record=record,
            nonvac_len=nonvac_len,
            p=float(p),
            corruption=corruption,
            delim=delim,
        )
        try:
            rec_micro = bhq.recover_message_from_single_stream(noisy, m=m, meta={})
            rec_bits = bhq.allowed_micro_indices_to_bits(rec_micro, allowed=allowed)
            rec_text = bhq._bits_to_ascii(rec_bits)
            if rec_text == msg_text:
                ok += 1
            else:
                wrong += 1
        except Exception:
            exc += 1

    tr = int(trials)
    ok_rate = ok / tr if tr else 0.0
    wrong_rate = wrong / tr if tr else 0.0
    exc_rate = exc / tr if tr else 0.0

    return {
        "m": str(int(m)),
        "mode": str(mode),
        "corr": str(corruption),
        "p": f"{float(p):.3f}",
        "trials": str(tr),
        "ok_rate": f"{ok_rate:.6f}",
        "wrong_rate": f"{wrong_rate:.6f}",
        "exc_rate": f"{exc_rate:.6f}",
    }


def main() -> None:
    m_list = [6, 12]
    modes = ["cyclic_only", "avoid_delim_esc"]
    corrs = ["safe", "full"]
    ps = [0.0, 0.01, 0.02, 0.05, 0.10]
    trials = 200
    seed0 = 20260112

    rows: List[str] = []
    for m in m_list:
        for mode in modes:
            for corr in corrs:
                for p in ps:
                    r = _run_trials(m=m, mode=mode, corruption=corr, p=p, trials=trials, seed=seed0)
                    rows.append(
                        " & ".join(
                            [
                                r["m"],
                                r["mode"],
                                r["corr"],
                                r["p"],
                                r["trials"],
                                r["ok_rate"],
                                r["wrong_rate"],
                                r["exc_rate"],
                            ]
                        )
                        + r" \\"
                    )
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_record_noise_audit_rows.tex", rows)

    summary = [
        r"\paragraph{Record-noise audit for the Page surrogate (interface robustness).} \AuditTag "
        r"This fragment perturbs the external stable-label record by bounded symbol substitutions in the non-vacuum "
        r"prefix and reports exact-recovery rates. This is an interface-level robustness diagnostic for the "
        r"single-stream recovery narrative: it separates 'internal unitarity' from 'operational recoverability under noise'.",
    ]
    write_lines(generated_dir() / "bh_page_record_noise_audit_summary.tex", summary)

    print("Wrote sections/generated/bh_page_record_noise_audit_rows.tex")
    print("Wrote sections/generated/bh_page_record_noise_audit_summary.tex")


if __name__ == "__main__":
    main()

