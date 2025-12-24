from __future__ import annotations

from pathlib import Path


def _run_script_capture(python_exe: str, script_path: str) -> list[str]:
    import subprocess

    out = subprocess.check_output([python_exe, script_path], text=True)
    return out.splitlines()


def build(out_dir: Path, *, png: bool = False) -> None:
    import os

    import matplotlib.pyplot as plt
    import numpy as np

    python_exe = os.environ.get("PYTHON", "") or os.sys.executable
    scripts_dir = Path(__file__).resolve().parents[1]
    script = scripts_dir / "experiment_11_slice_sampling_delta_tau_hecke_closure_table.py"

    lines = _run_script_capture(python_exe, str(script))

    # Parse two tables printed by the script:
    # 1) "n,tau(n),|error|,bound,log10_trunc_bound,ratio"
    # 2) "lhs,budget,ratio"
    in_tau = False
    in_hecke = False
    ns: list[int] = []
    taus: list[float] = []
    errs: list[float] = []
    bds: list[float] = []
    lhs = None
    budget = None

    for ln in lines:
        if "n,tau" in ln and "bound" in ln:
            in_tau = True
            in_hecke = False
            continue
        if "lhs" in ln and "budget" in ln:
            in_tau = False
            in_hecke = True
            continue
        if in_tau:
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) < 4:
                continue
            try:
                n = int(parts[0])
                tau_n = float(parts[1])
                err = float(parts[2])
                bd = float(parts[3])
            except ValueError:
                continue
            ns.append(n)
            taus.append(tau_n)
            errs.append(err)
            bds.append(bd)
        elif in_hecke:
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) < 2:
                continue
            try:
                lhs = float(parts[0])
                budget = float(parts[1])
            except ValueError:
                continue

    fig = plt.figure(figsize=(7.6, 3.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.6, 1.0])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    x = np.arange(len(ns), dtype=float)
    ax1.bar(x, errs, color="tab:gray", alpha=0.85, label=r"observed $|\hat{\tau}(n)-\tau(n)|$")
    ax1.bar(x, bds, color="tab:red", alpha=0.35, label="bound")
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(n) for n in ns])
    ax1.set_yscale("log")
    ax1.set_xlabel(r"index $n$")
    ax1.set_ylabel("absolute value (log scale)")
    ax1.set_title(r"Slice-sampling recovery on $\Delta$: errors vs bounds")
    ax1.legend(frameon=False, loc="best")

    # Hecke closure budget bar
    if lhs is None or budget is None:
        lhs = 0.0
        budget = 1.0
    ax2.bar([0], [lhs], color="tab:gray", alpha=0.85, label="lhs")
    ax2.bar([1], [budget], color="tab:red", alpha=0.35, label="budget")
    ax2.set_yscale("log")
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["lhs", "budget"])
    ax2.set_title(r"Certified Hecke closure ($p=2$)")
    ax2.legend(frameon=False, loc="best")

    fig.tight_layout()

    out_pdf = out_dir / "fig12_delta_tau_slice_sampling_closure.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig12_delta_tau_slice_sampling_closure.png", bbox_inches="tight")
    plt.close(fig)


