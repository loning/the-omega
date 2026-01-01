# -*- coding: utf-8 -*-
"""
Minimal dataset downloader + checksum utilities (standard library only).
Used by the full-results pipeline to fetch public corpora in a reproducible way.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import threading
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


def _human_bytes(n: int) -> str:
    n0 = float(max(0, int(n)))
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    u = 0
    while n0 >= 1024.0 and u < len(units) - 1:
        n0 /= 1024.0
        u += 1
    if u == 0:
        return f"{int(n0)}{units[u]}"
    return f"{n0:.1f}{units[u]}"


def _human_rate(bytes_per_s: float) -> str:
    if bytes_per_s <= 0:
        return "0B/s"
    return _human_bytes(int(bytes_per_s)) + "/s"


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
    progress_every_s: float = 60.0,
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
            t0_mono = time.monotonic()

            resume_from = tmp.stat().st_size if tmp.exists() else 0
            req_headers: dict[str, str] = {}
            if resume_from > 0:
                req_headers["Range"] = f"bytes={resume_from}-"
            req = _request_with_headers(url, req_headers)

            print(
                f"[download] {dst.name}: start (attempt {attempt}/{retries})",
                flush=True,
            )
            if resume_from > 0:
                print(
                    f"[download] {dst.name}: resuming from {_human_bytes(int(resume_from))}",
                    flush=True,
                )

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

                total_bytes: int | None = None
                try:
                    if int(code) == 206:
                        cr = r.headers.get("Content-Range") if r.headers else None
                        if isinstance(cr, str) and "/" in cr:
                            total_s = cr.split("/")[-1].strip()
                            if total_s.isdigit():
                                total_bytes = int(total_s)
                        cl = r.headers.get("Content-Length") if r.headers else None
                        if total_bytes is None and isinstance(cl, str) and cl.isdigit():
                            total_bytes = int(resume_from) + int(cl)
                    else:
                        cl = r.headers.get("Content-Length") if r.headers else None
                        if isinstance(cl, str) and cl.isdigit():
                            total_bytes = int(cl)
                except Exception:
                    total_bytes = None

                # Heartbeat progress reporter (prints at least once per minute for long downloads).
                progress: dict[str, object] = {"bytes": int(resume_from), "total": total_bytes}
                stop_evt = threading.Event()

                def _report() -> None:
                    if float(progress_every_s) <= 0:
                        return
                    while not stop_evt.wait(float(progress_every_s)):
                        b = int(progress.get("bytes") or 0)
                        tot = progress.get("total")
                        elapsed = time.monotonic() - t0_mono
                        rate = (float(b) - float(resume_from)) / elapsed if elapsed > 0 else 0.0
                        if isinstance(tot, int) and tot > 0:
                            pct = 100.0 * float(b) / float(tot)
                            print(
                                f"[download] {dst.name}: {_human_bytes(b)}/{_human_bytes(tot)} ({pct:.1f}%), {_human_rate(rate)}",
                                flush=True,
                            )
                        else:
                            print(
                                f"[download] {dst.name}: {_human_bytes(b)} downloaded, {_human_rate(rate)}",
                                flush=True,
                            )

                reporter = threading.Thread(target=_report, daemon=True)
                reporter.start()

                h = hashlib.sha256()
                n = 0
                if use_resume:
                    for b in iter_file_chunks(tmp):
                        h.update(b)
                        n += len(b)
                        progress["bytes"] = int(n)
                    fmode = "ab"
                else:
                    fmode = "wb"

                try:
                    with tmp.open(fmode) as f:
                        while True:
                            chunk = r.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            h.update(chunk)
                            n += len(chunk)
                            progress["bytes"] = int(n)
                    tmp.replace(dst)
                finally:
                    stop_evt.set()
                    reporter.join(timeout=1.0)

            sha = h.hexdigest()
            if expected_sha256 and sha.lower() != expected_sha256.lower():
                raise ValueError(f"SHA256 mismatch for {dst}: expected {expected_sha256}, got {sha}")
            _ = t0  # reserved for future timing logs
            elapsed2 = time.monotonic() - t0_mono
            rate2 = float(n) / elapsed2 if elapsed2 > 0 else 0.0
            print(
                f"[download] {dst.name}: done ({_human_bytes(int(n))} in {elapsed2:.1f}s, {_human_rate(rate2)})",
                flush=True,
            )
            return DownloadResult(url=url, path=dst, bytes=n, sha256=sha, retrieved_at_utc=utc_now_iso())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as e:
            last_err = e
            if attempt < retries:
                print(f"[download] {dst.name}: retry after error: {type(e).__name__}: {e}", flush=True)
                time.sleep(retry_sleep_s)
                continue
            raise
    assert last_err is not None
    raise last_err


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


