# -*- coding: utf-8 -*-
"""
Fetch FASTQ from NCBI SRA using sra-tools (fasterq-dump).

This helper is used by the H3-3c raw-read Ribo-seq pipeline.

Examples:
  python scripts/fetch_sra_fastq.py --srr SRR14517742 --out-dir data/riboseq_raw/GSE148965/fastq
  python scripts/fetch_sra_fastq.py --srr SRR14517742 --max-spots 1000000 --threads 8
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def run(cmd: list[str], *, check: bool = True) -> int:
    print("[cmd] " + " ".join(cmd), flush=True)
    p = subprocess.run(cmd)
    if check and p.returncode != 0:
        raise SystemExit(p.returncode)
    return int(p.returncode)


def _gzip_inplace(path: Path) -> None:
    if path.suffix == ".gz":
        return
    gz = path.with_suffix(path.suffix + ".gz")
    if gz.exists():
        return
    run(["gzip", "-f", str(path)])
    if not gz.exists():
        raise SystemExit(f"gzip failed to create: {gz}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch FASTQ from NCBI SRA via fasterq-dump.")
    ap.add_argument("--srr", action="append", default=[], help="Run accession (repeatable), e.g. SRR14517742.")
    ap.add_argument("--out-dir", default="", help="Output directory (default: data/_cache/sra_fastq/<SRR>/).")
    ap.add_argument("--tmp-dir", default="", help="Temp directory for fasterq-dump (default: <out-dir>/tmp).")
    ap.add_argument("--threads", type=int, default=8, help="Threads for fasterq-dump.")
    ap.add_argument("--max-spots", type=int, default=0, help="Optional max spots (0 disables).")
    ap.add_argument(
        "--tool",
        default="auto",
        choices=["auto", "fasterq-dump", "fastq-dump"],
        help="Which sra-tools extractor to use (auto tries fasterq-dump, then falls back to fastq-dump).",
    )
    ap.add_argument("--gzip", action="store_true", help="gzip output FASTQ in place.")
    ap.add_argument("--force", action="store_true", help="Re-download even if output files exist.")
    args = ap.parse_args()

    srrs = [str(x).strip() for x in (args.srr or []) if str(x).strip()]
    if not srrs:
        raise SystemExit("Provide at least one --srr SRR...")

    fasterq = shutil.which("fasterq-dump")
    fastq_dump = shutil.which("fastq-dump")
    if fasterq is None and fastq_dump is None:
        raise SystemExit("Missing `fasterq-dump`/`fastq-dump` in PATH (install sra-tools).")

    base_out = Path(str(args.out_dir).strip()) if str(args.out_dir).strip() else (root_dir() / "data" / "_cache" / "sra_fastq")
    if not base_out.is_absolute():
        base_out = root_dir() / base_out
    base_out.mkdir(parents=True, exist_ok=True)

    for srr in srrs:
        out_dir = base_out if str(args.out_dir).strip() else (base_out / srr)
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = Path(str(args.tmp_dir).strip()) if str(args.tmp_dir).strip() else (out_dir / "tmp")
        if not tmp_dir.is_absolute():
            tmp_dir = root_dir() / tmp_dir
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # fasterq-dump output naming depends on layout; for single-end this is usually <SRR>.fastq
        fastq = out_dir / f"{srr}.fastq"
        fastq_gz = fastq.with_suffix(fastq.suffix + ".gz")
        if (fastq.exists() or fastq_gz.exists()) and not args.force:
            print(f"[skip] exists: {fastq_gz if fastq_gz.exists() else fastq}", flush=True)
            continue

        preferred = str(args.tool).strip().lower()
        if preferred not in ("auto", "fasterq-dump", "fastq-dump"):
            preferred = "auto"

        def try_fasterq() -> bool:
            if fasterq is None:
                return False
            cmd = [
                fasterq,
                srr,
                "-O",
                str(out_dir),
                "--temp",
                str(tmp_dir),
                "--threads",
                str(int(args.threads)),
            ]
            if int(args.max_spots) > 0:
                cmd.extend(["--maxSpotId", str(int(args.max_spots))])
            rc = run(cmd, check=False)
            if rc == 0:
                return True
            print(f"[warn] fasterq-dump failed (rc={rc}); falling back to fastq-dump", flush=True)
            return False

        def run_fastq_dump() -> None:
            if fastq_dump is None:
                raise SystemExit("Missing `fastq-dump` in PATH.")
            cmd = [
                fastq_dump,
                srr,
                "--outdir",
                str(out_dir),
                "--split-3",
            ]
            if int(args.max_spots) > 0:
                cmd.extend(["-X", str(int(args.max_spots))])
            if args.gzip:
                cmd.append("--gzip")
            run(cmd)

        used = False
        if preferred == "fasterq-dump":
            used = try_fasterq()
            if not used:
                run_fastq_dump()
        elif preferred == "fastq-dump":
            run_fastq_dump()
            used = True
        else:
            used = try_fasterq()
            if not used:
                run_fastq_dump()

        # gzip if requested
        if args.gzip and fastq.exists() and preferred != "fastq-dump":
            _gzip_inplace(fastq)

        print(f"[ok] {srr} -> {out_dir}", flush=True)


if __name__ == "__main__":
    main()
