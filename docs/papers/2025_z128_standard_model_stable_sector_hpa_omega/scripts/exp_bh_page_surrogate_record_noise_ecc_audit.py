# -*- coding: utf-8 -*-
"""
BH5 audit: record-noise robustness with a finite-family error-correcting wrapper.

We wrap the external record with a repetition code at the symbol level:
  encode each stable label w as r repeats (r odd), decode by majority vote.
This is an interface-layer model of redundancy/correction in the record channel.

We sweep:
  - m in {6, 12}
  - mode in {cyclic_only, avoid_delim_esc}
  - corruption in {safe, full}  (same meaning as in exp_bh_page_surrogate_record_noise_audit.py)
  - p in a small finite family
  - r in {1, 3, 5, 7}

Outputs:
  - sections/generated/bh_page_record_noise_ecc_audit_rows.tex
  - sections/generated/bh_page_record_noise_ecc_audit_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import random
from typing import Dict, List

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
        if corruption == "safe":
            cand = [w for w in Xm if w != cur and w != delim]
        else:
            cand = [w for w in Xm if w != cur]
        if cand:
            out[i] = cand[rng.randrange(0, len(cand))]
    return out


def _rep_encode(record: List[str], r: int) -> List[str]:
    if int(r) <= 0 or (int(r) % 2) != 1:
        raise ValueError("r must be positive odd")
    out: List[str] = []
    for w in record:
        out.extend([w] * int(r))
    return out


def _rep_decode(record: List[str], r: int) -> List[str]:
    if int(r) <= 0 or (int(r) % 2) != 1:
        raise ValueError("r must be positive odd")
    if len(record) % int(r) != 0:
        raise RuntimeError("record length not divisible by r")
    out: List[str] = []
    for i in range(0, len(record), int(r)):
        block = record[i : i + int(r)]
        # majority vote
        counts: Dict[str, int] = {}
        for w in block:
            counts[w] = counts.get(w, 0) + 1
        best_w = None
        best_c = -1
        tie = False
        for w, c in counts.items():
            if c > best_c:
                best_c = c
                best_w = w
                tie = False
            elif c == best_c:
                tie = True
        if best_w is None or tie:
            raise RuntimeError("majority vote tie in repetition block")
        out.append(best_w)
    return out


def _run_trials(m: int, mode: str, corr: str, p: float, r: int, trials: int, seed: int) -> Dict[str, str]:
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

    # Apply ECC wrapper to the whole record (including tail).
    enc = _rep_encode(record, r=int(r))
    enc_nonvac_len = nonvac_len * int(r)

    ok = 0
    wrong = 0
    exc = 0
    for _ in range(int(trials)):
        rrng = random.Random(rng.randrange(0, 2**31 - 1))
        noisy = _corrupt_record(
            rng=rrng,
            Xm=Xm,
            record=enc,
            nonvac_len=enc_nonvac_len,
            p=float(p),
            corruption=corr,
            delim=delim,
        )
        try:
            dec = _rep_decode(noisy, r=int(r))
            rec_micro = bhq.recover_message_from_single_stream(dec, m=m, meta={})
            rec_bits = bhq.allowed_micro_indices_to_bits(rec_micro, allowed=allowed)
            rec_text = bhq._bits_to_ascii(rec_bits)
            if rec_text == msg_text:
                ok += 1
            else:
                wrong += 1
        except Exception:
            exc += 1

    tr = int(trials)
    return {
        "m": str(int(m)),
        "mode": str(mode),
        "corr": str(corr),
        "p": f"{float(p):.3f}",
        "r": str(int(r)),
        "trials": str(tr),
        "ok_rate": f"{(ok / tr) if tr else 0.0:.6f}",
        "wrong_rate": f"{(wrong / tr) if tr else 0.0:.6f}",
        "exc_rate": f"{(exc / tr) if tr else 0.0:.6f}",
    }


def main() -> None:
    m_list = [6, 12]
    modes = ["cyclic_only", "avoid_delim_esc"]
    corrs = ["safe", "full"]
    ps = [0.0, 0.01, 0.02, 0.05, 0.10]
    rs = [1, 3, 5, 7]
    trials = 200
    seed0 = 20260112

    rows: List[str] = []
    for m in m_list:
        for mode in modes:
            for corr in corrs:
                for p in ps:
                    for r in rs:
                        out = _run_trials(m=m, mode=mode, corr=corr, p=p, r=r, trials=trials, seed=seed0)
                        rows.append(
                            " & ".join(
                                [
                                    out["m"],
                                    out["mode"],
                                    out["corr"],
                                    out["p"],
                                    out["r"],
                                    out["trials"],
                                    out["ok_rate"],
                                    out["wrong_rate"],
                                    out["exc_rate"],
                                ]
                            )
                            + r" \\"
                        )
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_page_record_noise_ecc_audit_rows.tex", rows)

    summary = [
        r"\paragraph{Record-noise ECC audit (finite family).} \AuditTag "
        r"This fragment wraps the external record in a finite repetition-code family $r\\in\\{1,3,5,7\\}$ and "
        r"repeats the record-noise audit. This provides a minimal CAP-friendly route toward operational recovery "
        r"under bounded record corruption, separating the existence of recovery (unitarity in the record) from "
        r"noise-robust decodability.",
    ]
    write_lines(generated_dir() / "bh_page_record_noise_ecc_audit_summary.tex", summary)

    print("Wrote sections/generated/bh_page_record_noise_ecc_audit_rows.tex")
    print("Wrote sections/generated/bh_page_record_noise_ecc_audit_summary.tex")


if __name__ == "__main__":
    main()

