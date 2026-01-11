#!/usr/bin/env python3
"""
Toy audit for phase->delay numerical differentiation stability.

This script is intentionally simple, deterministic, and auditable.
It generates a one-channel unitary Breit–Wigner scattering model, injects
small phase noise, applies optional smoothing, and estimates the Wigner–Smith
delay via finite differences under a bounded family of discretization choices.

Writes:
  - sections/generated/force_phase_delay_audit_toy_rows.tex
  - sections/generated/force_phase_delay_audit_toy_summary.tex
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def moving_average(x: np.ndarray, w: int) -> np.ndarray:
    if w <= 1:
        return x
    # symmetric, deterministic padding
    pad = w // 2
    xpad = np.pad(x, (pad, pad), mode="edge")
    kernel = np.ones(w, dtype=float) / float(w)
    return np.convolve(xpad, kernel, mode="valid")


def central_diff(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    # central difference on interior points; endpoints use one-sided.
    dy = np.empty_like(y)
    dy[1:-1] = (y[2:] - y[:-2]) / (x[2:] - x[:-2])
    dy[0] = (y[1] - y[0]) / (x[1] - x[0])
    dy[-1] = (y[-1] - y[-2]) / (x[-1] - x[-2])
    return dy


def fmt(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    gen = root / "sections" / "generated"
    gen.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(0)

    # Breit–Wigner one-channel unitary model.
    omega0 = 0.0
    gamma = 1.0
    omega = np.linspace(-6.0, 6.0, 2401)

    S = (omega - omega0 - 1j * gamma / 2.0) / (omega - omega0 + 1j * gamma / 2.0)
    phase = np.unwrap(np.angle(S))
    tau_true = gamma / ((omega - omega0) ** 2 + (gamma / 2.0) ** 2)

    # Inject small additive phase noise (toy measurement model).
    sigma_phase = 1e-3
    phase_noisy = phase + sigma_phase * rng.normal(size=phase.shape)

    strides = [1, 2, 4]
    smooth_windows = [1, 7, 21]  # 1 means no smoothing

    rows = []
    best = None  # (median_abs_log, stride, w)

    eps = 1e-12
    for stride in strides:
        w_sub = omega[::stride]
        tau_ref = tau_true[::stride]
        for w in smooth_windows:
            ph = phase_noisy[::stride]
            ph_sm = moving_average(ph, w=w)
            # moving_average keeps length; omega aligned
            tau_est = central_diff(ph_sm, w_sub)

            # compare on magnitude (delay can be positive); use abs-log mismatch
            ratio = (np.abs(tau_est) + eps) / (np.abs(tau_ref) + eps)
            abslog = np.abs(np.log(ratio))
            med = float(np.median(abslog))
            mx = float(np.max(abslog))

            rows.append((stride, w, med, mx))
            if best is None or (med, mx, stride, w) < best:
                best = (med, mx, stride, w)

    row_lines = []
    for stride, w, med, mx in rows:
        label = f"stride={stride},w={w}"
        row_lines.append(f"{label} & {stride} & {w} & {fmt(med)} & {fmt(mx)} \\\\")

    (gen / "force_phase_delay_audit_toy_rows.tex").write_text(
        "\n".join(row_lines) + "\n",
        encoding="utf-8",
    )

    assert best is not None
    best_med, best_mx, best_stride, best_w = best
    summary = (
        "\\paragraph{Toy audit summary (phase$\\to$delay numerical stability).}\n"
        "\\AuditTag "
        "We generate a one-channel unitary Breit--Wigner model and estimate "
        "$\\tau(\\omega)=\\mathrm{d}\\delta/\\mathrm{d}\\omega$ from a noisy unwrapped phase "
        "under a bounded family of discretization choices (stride and smoothing window). "
        f"The best median abs-log mismatch in the declared family is {fmt(best_med)} "
        f"(max {fmt(best_mx)}) attained at stride={best_stride}, smoothing window w={best_w}.\n"
    )
    (gen / "force_phase_delay_audit_toy_summary.tex").write_text(summary, encoding="utf-8")

    print("Wrote sections/generated/force_phase_delay_audit_toy_rows.tex")
    print("Wrote sections/generated/force_phase_delay_audit_toy_summary.tex")


if __name__ == "__main__":
    main()

