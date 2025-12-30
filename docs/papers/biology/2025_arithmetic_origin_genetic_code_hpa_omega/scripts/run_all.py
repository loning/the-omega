# -*- coding: utf-8 -*-
"""
One-command end-to-end driver:
  - optional dataset fetch (data/manifest.json)
  - regenerate all LaTeX fragments (sections/generated/)
  - run transcriptome-scale RefSeq scan (sharded) and merge
  - build main.pdf via latexmk

Standard library only.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from exp_refseq_transcriptome import ANALYSIS_VERSION


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def run(cmd: list[str], *, cwd: Path) -> None:
    p = subprocess.run(cmd, cwd=str(cwd))
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reproduce all experiments and build the paper PDF.")
    p.add_argument("--download", action="store_true", help="Fetch public datasets per data/manifest.json.")
    p.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification for downloads.")
    p.add_argument("--refseq-stop-window", type=int, default=10, help="Stop-context window radius k for RefSeq scan.")
    p.add_argument("--recoding-k", type=int, default=10, help="Window radius k for recoding-site context.")
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cached results).")
    p.add_argument("--pdf", action="store_true", help="Build main.pdf with latexmk.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cwd = root_dir()

    # 1) Optional downloads
    if args.download:
        cmd = ["python3", "scripts/fetch_datasets.py", "--dataset", "all"]
        if args.insecure:
            cmd.append("--insecure")
        run(cmd, cwd=cwd)

    # 2) Core encoding scan + codon tables
    run(["python3", "scripts/exp_genetic_code_decompiler.py"], cwd=cwd)

    # 3) Nonstandard translation tables
    run(["python3", "scripts/exp_nonstandard_codes.py"], cwd=cwd)

    # 4) Recoding sites (Sec/Pyl)
    run(["python3", "scripts/exp_recoding_sites.py", "--k", str(int(args.recoding_k))], cwd=cwd)

    # 5) RefSeq transcriptome scan (sharded) + merge
    shards_dir = cwd / "data" / "refseq_hsapiens_mrna" / "shards" / f"k{int(args.refseq_stop_window)}_v{ANALYSIS_VERSION}"
    shards_dir.mkdir(parents=True, exist_ok=True)

    if args.force:
        for fp in shards_dir.glob("*.json"):
            fp.unlink()
        for fp in shards_dir.glob("*.meta.json"):
            fp.unlink()

    shard_files = sorted((cwd / "data" / "refseq_hsapiens_mrna").glob("human.*.rna.fna.gz"))
    if not shard_files:
        raise SystemExit("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/. Run with --download.")

    for fp in shard_files:
        out = shards_dir / f"{fp.name}.json"
        run(
            [
                "python3",
                "scripts/exp_refseq_transcriptome.py",
                "--input",
                str(fp.relative_to(cwd)),
                "--stop-window",
                str(int(args.refseq_stop_window)),
                "--no-latex",
                "--progress-every",
                "0",
                "--out-json",
                str(out.relative_to(cwd)),
                "--write-meta",
                *(["--force"] if args.force else []),
            ],
            cwd=cwd,
        )

    run(
        [
            "python3",
            "scripts/exp_refseq_transcriptome_merge.py",
            "--in-dir",
            str(shards_dir.relative_to(cwd)),
            "--out-json",
            str((cwd / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json").relative_to(cwd)),
        ],
        cwd=cwd,
    )

    # 6) Optional PDF build
    if args.pdf:
        # latexmk is the simplest robust driver; assume it is available in the environment.
        run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=cwd)


if __name__ == "__main__":
    main()


