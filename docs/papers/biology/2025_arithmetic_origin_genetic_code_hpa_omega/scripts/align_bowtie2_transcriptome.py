# -*- coding: utf-8 -*-
"""
Align (Ribo-seq) reads to a transcriptome FASTA with bowtie2 and produce a sorted BAM.

This is a small orchestration helper for the H3-3c raw-read pipeline:
  FASTQ -> bowtie2 -> BAM -> samtools sort/index
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> None:
    print("[cmd] " + " ".join(cmd), flush=True)
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _index_exists(prefix: Path) -> bool:
    # bowtie2-build creates either *.bt2 or *.bt2l (large index)
    return any(prefix.parent.glob(prefix.name + "*.bt2*"))


def _pipe_align_to_bam(*, bowtie2: str, samtools: str, cmd_align: list[str], out_bam: Path, threads: int) -> None:
    out_bam.parent.mkdir(parents=True, exist_ok=True)
    tmp_bam = out_bam.with_suffix(out_bam.suffix + ".tmp")

    print("[cmd] " + " ".join(cmd_align) + " | samtools view -b - | samtools sort ...", flush=True)
    p1 = subprocess.Popen(cmd_align, stdout=subprocess.PIPE)
    assert p1.stdout is not None
    p2 = subprocess.Popen([samtools, "view", "-b", "-"], stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    assert p2.stdout is not None
    p3 = subprocess.Popen([samtools, "sort", "-@", str(int(threads)), "-o", str(tmp_bam), "-"], stdin=p2.stdout)
    p2.stdout.close()

    rc3 = p3.wait()
    rc2 = p2.wait()
    rc1 = p1.wait()
    if rc1 != 0 or rc2 != 0 or rc3 != 0:
        raise SystemExit(f"Pipeline failed (bowtie2={rc1}, samtools view={rc2}, samtools sort={rc3}).")

    tmp_bam.replace(out_bam)
    run([samtools, "index", str(out_bam)])


def main() -> None:
    ap = argparse.ArgumentParser(description="Align reads to transcriptome with bowtie2 and emit sorted BAM.")
    ap.add_argument("--fastq", required=True, help="Input FASTQ (single-end).")
    ap.add_argument("--ref-fasta", required=True, help="Transcriptome FASTA (DNA alphabet).")
    ap.add_argument("--index-prefix", default="", help="bowtie2 index prefix (default: data/_cache/bowtie2/<ref-fasta-stem>).")
    ap.add_argument("--out-bam", default="", help="Output BAM path (default: <fastq-stem>.transcriptome.sorted.bam next to FASTQ).")
    ap.add_argument("--threads", type=int, default=8, help="Threads for bowtie2/samtools.")
    ap.add_argument("--force-index", action="store_true", help="Rebuild bowtie2 index even if present.")
    ap.add_argument("--force", action="store_true", help="Overwrite output BAM if present.")
    args = ap.parse_args()

    bowtie2 = shutil.which("bowtie2")
    bowtie2_build = shutil.which("bowtie2-build")
    samtools = shutil.which("samtools")
    if bowtie2 is None or bowtie2_build is None:
        raise SystemExit("Missing bowtie2/bowtie2-build in PATH.")
    if samtools is None:
        raise SystemExit("Missing samtools in PATH.")

    fastq = Path(str(args.fastq))
    if not fastq.is_absolute():
        fastq = root_dir() / fastq
    if not fastq.exists():
        raise SystemExit(f"Missing FASTQ: {fastq}")

    ref_fa = Path(str(args.ref_fasta))
    if not ref_fa.is_absolute():
        ref_fa = root_dir() / ref_fa
    if not ref_fa.exists():
        raise SystemExit(f"Missing ref FASTA: {ref_fa}")

    if str(args.index_prefix).strip():
        idx = Path(str(args.index_prefix).strip())
        if not idx.is_absolute():
            idx = root_dir() / idx
    else:
        idx = root_dir() / "data" / "_cache" / "bowtie2" / ref_fa.stem / ref_fa.stem
    idx.parent.mkdir(parents=True, exist_ok=True)

    if args.force_index or not _index_exists(idx):
        run([bowtie2_build, str(ref_fa), str(idx), "--threads", str(int(args.threads))])

    if str(args.out_bam).strip():
        out_bam = Path(str(args.out_bam).strip())
        if not out_bam.is_absolute():
            out_bam = root_dir() / out_bam
    else:
        out_bam = fastq.with_suffix("").with_suffix(".transcriptome.sorted.bam")

    if out_bam.exists() and not args.force:
        print(f"[skip] exists: {out_bam}", flush=True)
        return

    cmd_align = [
        bowtie2,
        "--very-sensitive-local",
        "-x",
        str(idx),
        "-U",
        str(fastq),
        "-p",
        str(int(args.threads)),
        "--no-unal",
        "-k",
        "1",
    ]
    _pipe_align_to_bam(bowtie2=bowtie2, samtools=samtools, cmd_align=cmd_align, out_bam=out_bam, threads=int(args.threads))
    print(f"[ok] {out_bam}", flush=True)


if __name__ == "__main__":
    main()

