# -*- coding: utf-8 -*-
"""
Validate the GitHub-Release data bundle under dist/.

Checks:
  - dist/*.meta.json is well-formed
  - archive sha256 + size match metadata
  - the tar.gz contains data/manifest.json and its sha256 matches metadata
  - (optional) local data/manifest.json sha256 matches metadata

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import time
from pathlib import Path
from typing import Any


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read {label}: {path}") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"Malformed {label}: {path}")
    return obj


def sha256_file_with_progress(path: Path, *, progress_every_s: float = 60.0) -> str:
    h = hashlib.sha256()
    n = 0
    t0 = time.monotonic()
    last = t0
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
            n += len(b)
            now = time.monotonic()
            if progress_every_s > 0 and (now - last) >= progress_every_s:
                dt = now - t0
                rate = (n / dt) if dt > 0 else 0.0
                print(f"[progress] sha256 {path.name}: bytes={n} elapsed_s={dt:.1f} rate_Bps={rate:.1f}", flush=True)
                last = now
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate dist/genetic-code-data.* bundle + metadata.")
    p.add_argument("--archive", default="dist/genetic-code-data.tar.gz", help="Archive path (relative to project root).")
    p.add_argument("--meta", default="dist/genetic-code-data.meta.json", help="Metadata JSON path (relative to project root).")
    p.add_argument(
        "--check-local-manifest",
        action="store_true",
        help="Also verify that local data/manifest.json sha256 matches metadata.",
    )
    p.add_argument("--progress-every-s", type=float, default=60.0, help="Progress heartbeat interval in seconds (0 disables).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    r = root_dir()
    archive = (r / str(args.archive)).resolve()
    meta_path = (r / str(args.meta)).resolve()

    if not archive.exists():
        raise SystemExit(f"Missing archive: {archive}")
    if not meta_path.exists():
        raise SystemExit(f"Missing meta JSON: {meta_path}")

    meta = _read_json_dict(meta_path, label="bundle meta")
    expected_sha = meta.get("archive_sha256")
    expected_bytes = meta.get("archive_bytes")
    expected_manifest_sha = meta.get("manifest_sha256")
    if not isinstance(expected_sha, str) or len(expected_sha) < 10:
        raise SystemExit(f"Missing/invalid archive_sha256 in {meta_path}")
    if not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise SystemExit(f"Missing/invalid archive_bytes in {meta_path}")
    if expected_manifest_sha is not None and (not isinstance(expected_manifest_sha, str) or len(expected_manifest_sha) < 10):
        raise SystemExit(f"Missing/invalid manifest_sha256 in {meta_path}")

    actual_bytes = archive.stat().st_size
    if int(actual_bytes) != int(expected_bytes):
        raise SystemExit(f"archive_bytes mismatch: meta={expected_bytes} actual={actual_bytes}")

    actual_sha = sha256_file_with_progress(archive, progress_every_s=float(args.progress_every_s))
    if actual_sha.lower() != str(expected_sha).lower():
        raise SystemExit(f"archive_sha256 mismatch: meta={expected_sha} actual={actual_sha}")

    # Validate manifest sha inside the archive if present in meta.
    if isinstance(expected_manifest_sha, str):
        with tarfile.open(str(archive), mode="r:gz") as tf:
            try:
                ti = tf.getmember("data/manifest.json")
            except KeyError as e:
                raise SystemExit("Archive missing data/manifest.json") from e
            f = tf.extractfile(ti)
            if f is None:
                raise SystemExit("Failed to read data/manifest.json from archive")
            content = f.read()
        man_sha_in_archive = sha256_bytes(content)
        if man_sha_in_archive.lower() != expected_manifest_sha.lower():
            raise SystemExit(
                f"manifest_sha256 mismatch: meta={expected_manifest_sha} archive_manifest={man_sha_in_archive}"
            )

        if bool(args.check_local_manifest):
            local_manifest = r / "data" / "manifest.json"
            if not local_manifest.exists():
                raise SystemExit(f"Missing local manifest.json: {local_manifest}")
            local_sha = sha256_file_with_progress(local_manifest, progress_every_s=float(args.progress_every_s))
            if local_sha.lower() != expected_manifest_sha.lower():
                raise SystemExit(
                    f"local manifest_sha256 mismatch: meta={expected_manifest_sha} local_manifest={local_sha}"
                )

    print("OK", flush=True)
    print(f"bundle_meta={meta_path.name}", flush=True)
    print(f"archive={archive.name} bytes={actual_bytes} sha256={actual_sha}", flush=True)
    if isinstance(expected_manifest_sha, str):
        print(f"manifest_sha256={expected_manifest_sha}", flush=True)


if __name__ == "__main__":
    main()


