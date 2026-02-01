#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal numerical checks for falsifiability fingerprints.

This script is intentionally lightweight: it reads the JSON artifacts produced
by scripts/run_all.py and computes a few scalar pass/fail checks to make the
paper's "fingerprints" auditable as numerical tests.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple


def _fib(n: int) -> int:
    """Fibonacci with F_1=F_2=1."""
    if n <= 0:
        return 0
    if n <= 2:
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _degeneracy_checks(deg_hist: Dict[str, int], m: int) -> Tuple[bool, Dict[str, Any]]:
    # deg_hist maps "fiber_size" -> count(types)
    total_types = int(sum(int(v) for v in deg_hist.values()))
    total_mass = int(sum(int(k) * int(v) for k, v in deg_hist.items()))
    expected_mass = 2**m
    expected_types = _fib(m + 2)  # for golden-mean language |X_m|=F_{m+2}
    ok_mass = total_mass == expected_mass
    ok_types = total_types == expected_types
    return (
        ok_mass and ok_types,
        {
            "m": m,
            "types_total": total_types,
            "types_expected_F_m_plus_2": expected_types,
            "mass_total": total_mass,
            "mass_expected_2_pow_m": expected_mass,
            "ok_mass": ok_mass,
            "ok_types": ok_types,
        },
    )


@dataclass(frozen=True)
class Thresholds:
    # These are intentionally conservative; they are not "physics claims".
    demo2d_peakiness_min: float = 0.15
    demo6d_envelope_lift_ratio_min: float = 1.30
    demo1d_entropy_rate_proxy_max: float = 0.30  # H(n)/n at max block n
    demo6d_correlated_autocorr_abs_min: float = 0.10
    demo6d_correlated_h_proxy_min: float = 0.05


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts"
    out_path = artifacts / "fingerprint_tests.json"

    th = Thresholds()
    results: Dict[str, Any] = {"thresholds": th.__dict__, "tests": {}}

    # Demo A (1D): zero-entropy sanity check via block entropy growth.
    d1 = _read_json(artifacts / "demo_1d_entropy_estimates.json")
    max_n = int(d1["params"]["max_block_len"])
    Hn = float(d1["block_entropy"][str(max_n)])
    h_proxy = Hn / max_n
    ok1 = h_proxy <= th.demo1d_entropy_rate_proxy_max
    results["tests"]["demo_1d_zero_entropy"] = {
        "max_block_len": max_n,
        "H_max_block": Hn,
        "H_over_n": h_proxy,
        "ok": ok1,
    }

    # Demo B (2D->1D): Fold degeneracy invariants + peakiness.
    d2 = _read_json(artifacts / "demo_2d_fingerprints.json")
    m2 = int(d2["params"]["fold_m"])
    ok_deg2, deg2 = _degeneracy_checks(d2["fold"]["degeneracy_histogram_exact"], m2)
    peakiness = float(d2["diffraction"]["peakiness"]["topK_frac"])
    ok_peak = peakiness >= th.demo2d_peakiness_min
    results["tests"]["demo_2d_fold_degeneracy"] = {**deg2, "ok": ok_deg2}
    results["tests"]["demo_2d_diffraction_peakiness"] = {
        "topK_frac": peakiness,
        "K": float(d2["diffraction"]["peakiness"]["K"]),
        "ok": ok_peak,
    }

    # Demo C (6D): box-window Fourier envelope consistency fit + Fold invariants.
    d6 = _read_json(artifacts / "demo_6d_fingerprints.json")
    m6 = int(d6["params"]["scan_fold_m"])
    ok_deg6, deg6 = _degeneracy_checks(d6["symbolic"]["degeneracy_histogram_exact"], m6)
    results["tests"]["demo_6d_fold_degeneracy"] = {**deg6, "ok": ok_deg6}

    # Correlated-noise robustness: ensure correlation is present and entropy proxy stays nontrivial.
    # Use the middle epsilon (if present) for a stable representative.
    eps_keys = list(d6["symbolic"]["by_eps"].keys())
    eps_keys_sorted = sorted(eps_keys, key=lambda s: float(s))
    eps_pick = eps_keys_sorted[len(eps_keys_sorted) // 2] if eps_keys_sorted else None
    ok_corr = True
    corr_details: Dict[str, Any] = {}
    if eps_pick is not None:
        corr = d6["symbolic"]["by_eps"][eps_pick]["raw_bits_correlated"]
        ac1 = float(corr.get("lag1_autocorr", 0.0))
        hpc = float(corr.get("h_proxy", 0.0))
        ok_corr = (abs(ac1) >= th.demo6d_correlated_autocorr_abs_min) and (hpc >= th.demo6d_correlated_h_proxy_min)
        corr_details = {"eps": float(eps_pick), "lag1_autocorr": ac1, "h_proxy": hpc, "ok": ok_corr}
    results["tests"]["demo_6d_correlated_noise"] = corr_details if corr_details else {"ok": False}

    box = _read_json(artifacts / "demo_6d_box_window_fourier.json")
    fit = box.get("fit", {})
    lift_ratio = float(fit.get("envelope_lift_ratio", float("nan")))
    ok_env = (not math.isnan(lift_ratio)) and lift_ratio >= th.demo6d_envelope_lift_ratio_min
    results["tests"]["demo_6d_box_window_envelope_fit"] = {
        "pearson_r": float(fit.get("pearson_r", float("nan"))),
        "spearman_r": float(fit.get("spearman_r", float("nan"))),
        "r2_linear": float(fit.get("r2_linear", float("nan"))),
        "r2_log10": float(fit.get("r2_log10", float("nan"))),
        "top_peaks_K": int(fit.get("top_peaks_K", 0)),
        "envelope_lift_ratio": lift_ratio,
        "ok": ok_env,
    }

    all_ok = all(bool(t.get("ok")) for t in results["tests"].values())
    results["all_ok"] = all_ok

    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[test_fingerprints] wrote: {out_path}", flush=True)
    print(f"[test_fingerprints] all_ok={all_ok}", flush=True)


if __name__ == "__main__":
    main()

