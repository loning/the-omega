# -*- coding: utf-8 -*-
"""
Build a GitHub-Release-ready data bundle for this paper project.

Outputs:
  - genetic-code-data.tar.gz        (contains data/...)
  - genetic-code-data.meta.json     (sha256 + size + manifest sha)

Standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import os
import tarfile
from pathlib import Path
from typing import Iterator

from data_manager import sha256_file, utc_now_iso, write_json


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def iter_files(base: Path) -> Iterator[Path]:
    for fp in sorted(base.rglob("*")):
        if fp.is_dir():
            continue
        yield fp


def should_exclude(rel_posix: str) -> bool:
    # Exclude caches and obvious test artifacts.
    if rel_posix.startswith("data/_release_cache/"):
        return True
    if rel_posix.endswith("/.DS_Store") or rel_posix.endswith(".DS_Store"):
        return True
    if rel_posix == "data/recoding_genbank/recoding_sites.test.jsonl":
        return True
    if rel_posix.startswith("data/refseq_hsapiens_mrna/shards/") and "/test_" in ("/" + rel_posix):
        return True
    return False


def add_file(tf: tarfile.TarFile, fp: Path, *, arcname: str) -> None:
    ti = tf.gettarinfo(str(fp), arcname=arcname)
    # Normalize metadata to reduce unnecessary diffs.
    ti.uid = 0
    ti.gid = 0
    ti.uname = ""
    ti.gname = ""
    ti.mtime = 0
    with fp.open("rb") as f:
        tf.addfile(ti, fileobj=f)


def build_bundle(*, out_dir: Path, archive_name: str, meta_name: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    r = root_dir()
    data_dir = r / "data"
    if not data_dir.exists():
        raise SystemExit(f"Missing data directory: {data_dir}")

    archive_path = out_dir / archive_name
    meta_path = out_dir / meta_name

    tmp = archive_path.with_suffix(archive_path.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    # Deterministic gzip header (mtime=0).
    with tmp.open("wb") as f_out:
        with gzip.GzipFile(fileobj=f_out, mode="wb", compresslevel=9, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tf:
                for fp in iter_files(data_dir):
                    rel = fp.relative_to(r).as_posix()
                    if should_exclude(rel):
                        continue
                    add_file(tf, fp, arcname=rel)

    tmp.replace(archive_path)

    manifest_path = data_dir / "manifest.json"
    manifest_sha = sha256_file(manifest_path) if manifest_path.exists() else None
    archive_sha = sha256_file(archive_path)
    archive_bytes = archive_path.stat().st_size

    # Compute total bytes of included files (best-effort; not authoritative for extraction).
    total_included = 0
    for fp in iter_files(data_dir):
        rel = fp.relative_to(r).as_posix()
        if should_exclude(rel):
            continue
        total_included += fp.stat().st_size

    meta = {
        "created_at_utc": utc_now_iso(),
        "archive_name": archive_name,
        "archive_bytes": int(archive_bytes),
        "archive_sha256": archive_sha,
        "included_total_bytes": int(total_included),
        "manifest_path": "data/manifest.json",
        "manifest_sha256": manifest_sha,
        "layout": "tar.gz containing a top-level data/ directory (extract at project root)",
    }
    write_json(meta_path, meta)

    return archive_path, meta_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build GitHub Release data bundle + metadata.")
    p.add_argument("--out-dir", default="dist", help="Output directory (relative to project root).")
    p.add_argument("--archive-name", default="genetic-code-data.tar.gz", help="Archive filename.")
    p.add_argument("--meta-name", default="genetic-code-data.meta.json", help="Metadata filename.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = root_dir() / str(args.out_dir)
    archive, meta = build_bundle(out_dir=out_dir, archive_name=str(args.archive_name), meta_name=str(args.meta_name))
    print("Wrote:", archive)
    print("Wrote:", meta)


if __name__ == "__main__":
    main()


