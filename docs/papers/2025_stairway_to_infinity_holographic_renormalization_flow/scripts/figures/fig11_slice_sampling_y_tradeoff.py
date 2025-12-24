from __future__ import annotations

from pathlib import Path


def _run_script_capture(python_exe: str, script_path: str) -> list[str]:
    import subprocess

    out = subprocess.check_output([python_exe, script_path], text=True)
    return out.splitlines()


def build(out_dir: Path, *, png: bool = False) -> None:
    import os

    import matplotlib.pyplot as plt

    python_exe = os.environ.get("PYTHON", "") or os.sys.executable
    scripts_dir = Path(__file__).resolve().parents[1]
    script = scripts_dir / "experiment_07_slice_sampling_e4_y_tradeoff_table.py"

    lines = _run_script_capture(python_exe, str(script))

    # Expect CSV rows after header: y,|q|,|error|,bound,log10_trunc_bound,ratio
    started = False
    ys: list[float] = []
    errs: list[float] = []
    bds: list[float] = []
    for ln in lines:
        if "y," in ln and "error" in ln:
            started = True
            continue
        if not started:
            continue
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 4:
            continue
        try:
            y = float(parts[0])
            err = float(parts[2])
            bd = float(parts[3])
        except ValueError:
            continue
        ys.append(y)
        errs.append(err)
        bds.append(bd)

    fig, ax = plt.subplots(figsize=(6.9, 3.6))
    ax.semilogy(ys, errs, marker="o", label="observed error")
    ax.semilogy(ys, bds, marker="s", linestyle="--", label="explicit bound")
    ax.set_xlabel(r"height $y$")
    ax.set_ylabel("absolute value")
    ax.set_title(r"Slice-sampling height trade-off (fixed $N$)")
    ax.legend(frameon=False, loc="best")

    out_pdf = out_dir / "fig11_slice_sampling_y_tradeoff.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig11_slice_sampling_y_tradeoff.png", bbox_inches="tight")
    plt.close(fig)


