from __future__ import annotations

import argparse
import importlib
import random
import sys
from pathlib import Path


def _configure_matplotlib() -> None:
    import matplotlib as mpl

    mpl.use("Agg")
    mpl.rcParams.update(
        {
            "figure.figsize": (6.4, 3.8),
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "legend.fontsize": 9,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.7,
            "lines.linewidth": 1.6,
            "lines.markersize": 4.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.usetex": False,
            "mathtext.fontset": "dejavusans",
            "font.family": "DejaVu Sans",
        }
    )


def _set_reproducible_seed(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except Exception:
        pass


def _available_figures() -> list[str]:
    return [
        "fig01_layers_flow",
        "fig02_stairway_pipeline",
    ]


def main() -> int:
    here = Path(__file__).resolve()
    scripts_dir = here.parent
    paper_dir = scripts_dir.parent
    fig_modules_dir = scripts_dir / "figures"
    out_dir_default = paper_dir / "figures"

    parser = argparse.ArgumentParser(description="Build reproducible paper figures (PDF).")
    parser.add_argument("--out-dir", type=Path, default=out_dir_default, help="Output directory for figures.")
    parser.add_argument("--only", nargs="*", default=None, help="Subset of figures to build (by id).")
    parser.add_argument("--list", action="store_true", help="List available figures and exit.")
    parser.add_argument("--png", action="store_true", help="Also write PNG previews.")
    parser.add_argument("--seed", type=int, default=0, help="Reproducibility seed (default: 0).")
    args = parser.parse_args()

    figs = _available_figures()
    if args.list:
        for f in figs:
            print(f)
        return 0

    selected = figs if not args.only else args.only
    unknown = [f for f in selected if f not in figs]
    if unknown:
        raise SystemExit(f"Unknown figure id(s): {unknown}. Use --list to see options.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    _set_reproducible_seed(args.seed)
    _configure_matplotlib()

    sys.path.insert(0, str(fig_modules_dir))

    for fig_id in selected:
        mod = importlib.import_module(fig_id)
        if not hasattr(mod, "build"):
            raise SystemExit(f"Figure module {fig_id} has no build(out_dir, png=...) function.")
        print(f"[build] {fig_id}")
        mod.build(args.out_dir, png=args.png)

    print(f"Done. Wrote figures to: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


