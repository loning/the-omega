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
    p.add_argument("--download", dest="download", action="store_true", help="Fetch latest data bundle (GitHub Release) and/or upstream datasets.")
    p.add_argument("--no-download", dest="download", action="store_false", help="Do not fetch any datasets; assume data/ is already present.")
    p.set_defaults(download=True)
    p.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification for downloads.")
    p.add_argument("--refseq-stop-window", type=int, default=10, help="Stop-context window radius k for RefSeq scan.")
    p.add_argument(
        "--refseq-stop-window-list",
        default="3,5,10,20",
        help="Comma-separated list of stop-context window radii k to compute in one pass (empty disables).",
    )
    p.add_argument(
        "--refseq-progress-every",
        type=int,
        default=20000,
        help="Print progress every N records per RefSeq shard (0 disables).",
    )
    p.add_argument(
        "--refseq-max-records",
        type=int,
        default=0,
        help="Optional max records per RefSeq shard for quick runs (0 = no limit).",
    )
    p.add_argument(
        "--refseq-max-shards",
        type=int,
        default=0,
        help="Optional max number of RefSeq shard files to process (0 = all).",
    )
    p.add_argument("--recoding-k", type=int, default=10, help="Window radius k for recoding-site context.")
    p.add_argument(
        "--recoding-k-list",
        default="3,5,10,20",
        help="Comma-separated list of window radii k for recoding-site context (empty disables).",
    )
    p.add_argument("--recoding-max-files", type=int, default=0, help="Optional limit on number of GenBank files for recoding (0=all).")
    p.add_argument("--panel-max-records", type=int, default=0, help="Optional max records per dataset for corpus panel (0 = no limit).")
    p.add_argument("--nonstandard-max-records", type=int, default=0, help="Optional max records per dataset for nonstandard sequence tests (0 = no limit).")
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cached results).")
    p.add_argument("--pdf", action="store_true", help="Build main.pdf with latexmk.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cwd = root_dir()

    refseq_quick = int(args.refseq_max_records) > 0 or int(args.refseq_max_shards) > 0
    recoding_quick = int(args.recoding_max_files) > 0
    panel_quick = int(args.panel_max_records) > 0
    nonstandard_quick = int(args.nonstandard_max_records) > 0

    quick_dir = cwd / "data" / "_quick" / "run_all"

    # 1) Optional downloads
    if args.download:
        cmd = ["python3", "scripts/fetch_datasets.py", "--dataset", "all"]
        if args.insecure:
            cmd.append("--insecure")
        run(cmd, cwd=cwd)

    # 2) Core encoding scan + codon tables
    run(["python3", "scripts/exp_genetic_code_decompiler.py"], cwd=cwd)

    # 2b) Fold_m resolution scan (m>6)
    run(["python3", "scripts/exp_foldm_resolution_scan.py"], cwd=cwd)

    # 3) Nonstandard translation tables
    run(["python3", "scripts/exp_nonstandard_codes.py"], cwd=cwd)

    # 4) Recoding sites (Sec/Pyl)
    rec_cmd = ["python3", "scripts/exp_recoding_sites.py", "--k", str(int(args.recoding_k))]
    if str(args.recoding_k_list or "").strip():
        rec_cmd += ["--k-list", str(args.recoding_k_list)]
    if int(args.recoding_max_files) > 0:
        rec_cmd += ["--max-files", str(int(args.recoding_max_files))]
    if recoding_quick:
        quick_dir.mkdir(parents=True, exist_ok=True)
        rec_cmd += [
            "--no-latex",
            "--out-jsonl",
            str((quick_dir / "recoding_sites.jsonl").relative_to(cwd)),
            "--out-summary-json",
            str((quick_dir / "recoding_sites_summary.json").relative_to(cwd)),
        ]
    if args.force:
        rec_cmd += ["--force"]
    run(rec_cmd, cwd=cwd)

    # 5) RefSeq transcriptome scan (sharded) + merge
    if refseq_quick:
        quick_dir.mkdir(parents=True, exist_ok=True)
        shards_dir = quick_dir / "refseq_shards" / f"k{int(args.refseq_stop_window)}_v{ANALYSIS_VERSION}_mr{int(args.refseq_max_records)}_ms{int(args.refseq_max_shards)}"
        merge_out_json = quick_dir / "transcriptome_summary.json"
    else:
        shards_dir = cwd / "data" / "refseq_hsapiens_mrna" / "shards" / f"k{int(args.refseq_stop_window)}_v{ANALYSIS_VERSION}"
        merge_out_json = cwd / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"
    shards_dir.mkdir(parents=True, exist_ok=True)

    if args.force:
        for fp in shards_dir.glob("*.json"):
            fp.unlink()
        for fp in shards_dir.glob("*.meta.json"):
            fp.unlink()

    shard_files = sorted((cwd / "data" / "refseq_hsapiens_mrna").glob("human.*.rna.fna.gz"))
    if not shard_files:
        raise SystemExit("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/. Run with --download.")
    if int(args.refseq_max_shards) > 0:
        shard_files = shard_files[: int(args.refseq_max_shards)]

    for fp in shard_files:
        out = shards_dir / f"{fp.name}.json"
        refseq_cmd = [
            "python3",
            "scripts/exp_refseq_transcriptome.py",
            "--input",
            str(fp.relative_to(cwd)),
            "--stop-window",
            str(int(args.refseq_stop_window)),
        ]
        if str(args.refseq_stop_window_list or "").strip():
            refseq_cmd += ["--stop-window-list", str(args.refseq_stop_window_list)]
        refseq_cmd += [
            "--no-latex",
            "--progress-every",
            str(int(args.refseq_progress_every)),
            "--max-records",
            str(int(args.refseq_max_records)),
            "--out-json",
            str(out.relative_to(cwd)),
            "--write-meta",
            *(["--force"] if args.force else []),
        ]
        run(
            refseq_cmd,
            cwd=cwd,
        )

    merge_cmd = [
        "python3",
        "scripts/exp_refseq_transcriptome_merge.py",
        "--in-dir",
        str(shards_dir.relative_to(cwd)),
        "--out-json",
        str(merge_out_json.relative_to(cwd)),
        *(["--no-latex"] if refseq_quick else []),
        *(["--force"] if args.force else []),
    ]
    run(merge_cmd, cwd=cwd)

    # 6) Cross-domain corpus panel + sequence-level nonstandard-code tests.
    panel_cmd = ["python3", "scripts/exp_corpus_panel.py", "--panel", "corpus_panel_v1"]
    if int(args.panel_max_records) > 0:
        panel_cmd += ["--max-records", str(int(args.panel_max_records))]
    if panel_quick:
        quick_dir.mkdir(parents=True, exist_ok=True)
        panel_cmd += [
            "--no-latex",
            "--out-json",
            str((quick_dir / "corpus_panel_summary.json").relative_to(cwd)),
        ]
    if args.force:
        panel_cmd += ["--force"]
    run(panel_cmd, cwd=cwd)

    ns_cmd = ["python3", "scripts/exp_nonstandard_sequence_tests.py", "--panel", "nonstandard_examples_v1"]
    if int(args.nonstandard_max_records) > 0:
        ns_cmd += ["--max-records", str(int(args.nonstandard_max_records))]
    if nonstandard_quick:
        quick_dir.mkdir(parents=True, exist_ok=True)
        ns_cmd += [
            "--no-latex",
            "--out-json",
            str((quick_dir / "nonstandard_sequence_tests.json").relative_to(cwd)),
        ]
    if args.force:
        ns_cmd += ["--force"]
    run(ns_cmd, cwd=cwd)

    # 7) Optional PDF build
    if args.pdf:
        # latexmk is the simplest robust driver; assume it is available in the environment.
        run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=cwd)


if __name__ == "__main__":
    main()


