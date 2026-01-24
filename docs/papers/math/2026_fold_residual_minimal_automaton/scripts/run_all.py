#!/usr/bin/env python3
"""
Entry point for all reproducible experiments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_root_from_this_file() -> Path:
    # .../docs/papers/math/<paper>/scripts/run_all.py
    return Path(__file__).resolve().parents[5]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mmax", type=int, default=20, help="max m for scanning")
    args = parser.parse_args()

    repo_root = _repo_root_from_this_file()
    paper_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(paper_dir / "scripts"))

    from exp_minimal_transducer_states import run_experiment  # noqa: E402

    print(f"[run_all] repo_root={repo_root}")
    print(f"[run_all] paper_dir={paper_dir}")
    run_experiment(paper_dir=paper_dir, mmax=args.mmax)
    print("[run_all] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

