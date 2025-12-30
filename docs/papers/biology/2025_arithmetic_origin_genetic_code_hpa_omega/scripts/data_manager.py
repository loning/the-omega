# -*- coding: utf-8 -*-
"""
Minimal dataset downloader + checksum utilities (standard library only).
Used by the full-results pipeline to fetch public corpora in a reproducible way.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


USER_AGENT = "the-omega-genetic-code/1.0 (+standard-library)"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_file_chunks(path: Path, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            yield b


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    for b in iter_file_chunks(path):
        h.update(b)
    return h.hexdigest()


@dataclass(frozen=True)
class DownloadResult:
    url: str
    path: Path
    bytes: int
    sha256: str
    retrieved_at_utc: str


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

def _request_with_headers(url: str, headers: dict[str, str]) -> urllib.request.Request:
    merged = {"User-Agent": USER_AGENT}
    merged.update(headers)
    return urllib.request.Request(url, headers=merged)


def ssl_context(*, verify: bool) -> ssl.SSLContext | None:
    """
    Return an SSLContext for urllib. If verify is False, disable certificate verification.
    Use verify=True by default; only disable verification when required by the runtime environment.
    """
    if verify:
        return None
    return ssl._create_unverified_context()


def download_file(
    url: str,
    dst: Path,
    *,
    expected_sha256: str | None = None,
    timeout_s: float = 120.0,
    chunk_size: int = 1024 * 1024,
    retries: int = 3,
    retry_sleep_s: float = 2.0,
    verify_ssl: bool = True,
) -> DownloadResult:
    """
    Download URL to dst (streaming), compute sha256. If expected_sha256 is provided and the
    existing file matches, skip download.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)

    # If file already exists, do not re-download; compute sha256 and return.
    if dst.exists():
        actual = sha256_file(dst)
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            raise ValueError(f"SHA256 mismatch for {dst}: expected {expected_sha256}, got {actual}")
        return DownloadResult(
            url=url,
            path=dst,
            bytes=dst.stat().st_size,
            sha256=actual,
            retrieved_at_utc=utc_now_iso(),
        )

    last_err: Exception | None = None
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    for attempt in range(1, retries + 1):
        try:
            t0 = time.time()

            resume_from = tmp.stat().st_size if tmp.exists() else 0
            req_headers: dict[str, str] = {}
            if resume_from > 0:
                req_headers["Range"] = f"bytes={resume_from}-"
            req = _request_with_headers(url, req_headers)

            with urllib.request.urlopen(
                req,
                timeout=timeout_s,
                context=ssl_context(verify=verify_ssl),
            ) as r:
                code = getattr(r, "status", None) or r.getcode()

                # If server ignored Range (or Range invalid), restart from scratch.
                use_resume = resume_from > 0 and int(code) == 206
                if not use_resume:
                    resume_from = 0

                h = hashlib.sha256()
                n = 0
                if use_resume:
                    for b in iter_file_chunks(tmp):
                        h.update(b)
                        n += len(b)
                    fmode = "ab"
                else:
                    fmode = "wb"

                with tmp.open(fmode) as f:
                    while True:
                        chunk = r.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        h.update(chunk)
                        n += len(chunk)
                tmp.replace(dst)
            sha = h.hexdigest()
            if expected_sha256 and sha.lower() != expected_sha256.lower():
                raise ValueError(f"SHA256 mismatch for {dst}: expected {expected_sha256}, got {sha}")
            _ = t0  # reserved for future timing logs
            return DownloadResult(url=url, path=dst, bytes=n, sha256=sha, retrieved_at_utc=utc_now_iso())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(retry_sleep_s)
                continue
            raise
    assert last_err is not None
    raise last_err


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


