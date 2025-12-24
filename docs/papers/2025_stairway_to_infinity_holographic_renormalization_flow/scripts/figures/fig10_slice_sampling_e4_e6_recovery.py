from __future__ import annotations

from pathlib import Path


def _parse_table_lines(lines: list[str]) -> tuple[list[float], list[float], list[float]]:
    # Expect CSV: N, D*, |error|, bound, ...
    ns: list[float] = []
    errs: list[float] = []
    bounds: list[float] = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 4:
            continue
        try:
            n = float(parts[0])
            err = float(parts[2])
            bd = float(parts[3])
        except ValueError:
            continue
        ns.append(n)
        errs.append(err)
        bounds.append(bd)
    return ns, errs, bounds


def _run_script_capture(python_exe: str, script_path: str) -> list[str]:
    import subprocess

    out = subprocess.check_output([python_exe, script_path], text=True)
    return out.splitlines()


def build(out_dir: Path, *, png: bool = False) -> None:
    import os

    import matplotlib.pyplot as plt

    # Use the running interpreter for compatibility (intended: root .venv python).
    python_exe = os.environ.get("PYTHON", "") or os.sys.executable
    scripts_dir = Path(__file__).resolve().parents[1]  # .../scripts

    e4_script = scripts_dir / "experiment_06_slice_sampling_e4_coeff_recovery_table.py"
    e6_script = scripts_dir / "experiment_10_slice_sampling_e6_coeff_recovery_table.py"

    e4_lines = _run_script_capture(python_exe, str(e4_script))
    e6_lines = _run_script_capture(python_exe, str(e6_script))

    # Extract the numeric rows after the header line containing "N,".
    def extract_after_header(lines: list[str]) -> list[str]:
        out: list[str] = []
        started = False
        for ln in lines:
            if "N," in ln and "error" in ln:
                started = True
                continue
            if started:
                out.append(ln)
        return out

    e4_ns, e4_err, e4_bd = _parse_table_lines(extract_after_header(e4_lines))
    e6_ns, e6_err, e6_bd = _parse_table_lines(extract_after_header(e6_lines))

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.loglog(e4_ns, e4_err, marker="o", label=r"$E_4$: observed $|\hat a_1-240|$")
    ax.loglog(e4_ns, e4_bd, marker="o", linestyle="--", label=r"$E_4$: bound")
    ax.loglog(e6_ns, e6_err, marker="s", label=r"$E_6$: observed $|\hat a_1-(-504)|$")
    ax.loglog(e6_ns, e6_bd, marker="s", linestyle="--", label=r"$E_6$: bound")
    ax.set_xlabel(r"$N$")
    ax.set_ylabel("absolute value")
    ax.set_title("Slice-sampling coefficient recovery (observed vs explicit bound)")
    ax.legend(frameon=False, loc="best")

    out_pdf = out_dir / "fig10_slice_sampling_e4_e6_recovery.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig10_slice_sampling_e4_e6_recovery.png", bbox_inches="tight")
    plt.close(fig)


