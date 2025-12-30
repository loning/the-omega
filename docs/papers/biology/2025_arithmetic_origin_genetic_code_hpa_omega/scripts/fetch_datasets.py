# -*- coding: utf-8 -*-
"""
Fetch public datasets described in data/manifest.json and update checksums in-place.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import tarfile
import re
import urllib.parse
import urllib.request
import time
from pathlib import Path
from typing import Any

from data_manager import download_file, read_json, sha256_file, ssl_context, utc_now_iso, write_json


DEFAULT_GITHUB_REPO = "loning/the-omega"
DEFAULT_GITHUB_RELEASE_TAG = "latest"
DEFAULT_GITHUB_RELEASE_ASSET_NAME = "genetic-code-data.tar.gz"
DEFAULT_GITHUB_RELEASE_META_NAME = "genetic-code-data.meta.json"
_KNOWN_RELEASE_SHA256: dict[str, str] = {
    # Pinned historical releases (optional). New releases should ship a meta JSON file so
    # the downloader can verify integrity without hardcoding SHA256 in the codebase.
    "genetic-code-data-v1.0": "53246e0563de007d85c9ec15e1991004a7ff237f966ab26eac3abb836e248ae7",
}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def manifest_path() -> Path:
    return root_dir() / "data" / "manifest.json"

def data_root() -> Path:
    return root_dir() / "data"


def _abs_path(rel: str) -> Path:
    return root_dir() / rel


def _download_text(
    url: str,
    *,
    timeout_s: float = 60.0,
    verify_ssl: bool = True,
    retries: int = 4,
    retry_sleep_s: float = 2.0,
) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "the-omega-genetic-code/1.0"})
    last_err: Exception | None = None
    for attempt in range(int(retries)):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context(verify=verify_ssl)) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001 - network layer raises several exception types
            last_err = e
            if attempt + 1 >= int(retries):
                break
            time.sleep(retry_sleep_s * float(attempt + 1))
    assert last_err is not None
    raise last_err


def fetch_gc_prt(m: dict[str, Any], *, verify_ssl: bool) -> None:
    ds = m["datasets"]["ncbi_gc_prt"]
    url = ds["url"]
    dst = _abs_path(ds["local_path"])
    res = download_file(url, dst, verify_ssl=verify_ssl)
    ds["bytes"] = res.bytes
    ds["sha256"] = res.sha256
    ds["retrieved_at_utc"] = res.retrieved_at_utc


def fetch_refseq_hsapiens_mrna(m: dict[str, Any], *, verify_ssl: bool) -> None:
    ds = m["datasets"]["refseq_hsapiens_mrna"]
    base_url = ds["base_url"].rstrip("/") + "/"
    index_url = base_url + ds["index_file"]
    include_re = re.compile(ds["include_regex"])

    local_dir = _abs_path(ds["local_dir"])
    local_dir.mkdir(parents=True, exist_ok=True)

    # Download md5checksums.txt to discover file list.
    md5_text = _download_text(index_url, timeout_s=120.0, verify_ssl=verify_ssl)
    names: list[str] = []
    md5_map: dict[str, str] = {}
    for line in md5_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        md5 = parts[0]
        name = parts[-1]
        if include_re.match(name):
            names.append(name)
            md5_map[name] = md5

    names = sorted(set(names))
    files_out: list[dict[str, Any]] = []
    for name in names:
        url = base_url + name
        dst = local_dir / name
        # We compute sha256 for reproducibility; md5 from NCBI index is recorded as additional info.
        res = download_file(
            url,
            dst,
            verify_ssl=verify_ssl,
            timeout_s=600.0,
            retries=6,
            retry_sleep_s=5.0,
        )
        files_out.append(
            {
                "name": name,
                "url": url,
                "bytes": res.bytes,
                "sha256": res.sha256,
                "retrieved_at_utc": res.retrieved_at_utc,
                "ncbi_md5": md5_map.get(name),
            }
        )

    ds["files"] = files_out
    ds["retrieved_at_utc"] = utc_now_iso()


def _eutils_esearch(db: str, term: str, retmax: int, *, verify_ssl: bool) -> list[str]:
    # NCBI recommends <=3 requests/second without an API key.
    time.sleep(0.4)
    q = {
        "db": db,
        "term": term,
        "retmax": str(int(retmax)),
        "retmode": "json",
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(q)
    txt = _download_text(url, timeout_s=120.0, verify_ssl=verify_ssl, retries=6, retry_sleep_s=2.0)
    obj = json.loads(txt)
    ids = obj.get("esearchresult", {}).get("idlist", [])
    return [str(x) for x in ids]


def _eutils_efetch_genbank(db: str, ids: list[str], *, verify_ssl: bool) -> str:
    # NCBI recommends <=3 requests/second without an API key.
    time.sleep(0.4)
    # Use comma-separated ids; chunking handled by caller.
    q = {
        "db": db,
        "id": ",".join(ids),
        "rettype": "gb",
        "retmode": "text",
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(q)
    return _download_text(url, timeout_s=240.0, verify_ssl=verify_ssl, retries=6, retry_sleep_s=3.0)


def _eutils_esummary_accessionversions(db: str, ids: list[str], *, verify_ssl: bool) -> dict[str, str]:
    """
    Return mapping {uid -> accessionversion} for nuccore IDs using E-utilities esummary.
    """
    if not ids:
        return {}
    # NCBI recommends <=3 requests/second without an API key.
    time.sleep(0.4)
    q = {
        "db": db,
        "id": ",".join(ids),
        "retmode": "json",
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urllib.parse.urlencode(q)
    txt = _download_text(url, timeout_s=120.0, verify_ssl=verify_ssl, retries=6, retry_sleep_s=2.0)
    obj = json.loads(txt)
    res = obj.get("result", {}) or {}
    uids = res.get("uids", []) or []
    out: dict[str, str] = {}
    for uid in uids:
        uid_s = str(uid)
        item = res.get(uid_s, {}) or {}
        acc = item.get("accessionversion") or item.get("accession")
        if acc:
            out[uid_s] = str(acc)
    return out


def _split_genbank_records(text: str) -> list[str]:
    # Records end with a line containing only '//'
    parts = []
    cur: list[str] = []
    for line in text.splitlines(keepends=True):
        cur.append(line)
        if line.strip() == "//":
            parts.append("".join(cur))
            cur = []
    if cur:
        # trailing fragment (should not happen)
        parts.append("".join(cur))
    return parts


def _genbank_accession(record: str) -> str | None:
    # Prefer VERSION, then ACCESSION.
    for line in record.splitlines():
        if line.startswith("VERSION"):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].strip()
    for line in record.splitlines():
        if line.startswith("ACCESSION"):
            parts = line.split()
            if len(parts) >= 2:
                return parts[1].strip()
    return None


def fetch_recoding_genbank(m: dict[str, Any], *, verify_ssl: bool) -> None:
    ds = m["datasets"]["ncbi_recoding_genbank"]
    local_dir = _abs_path(ds["local_dir"])
    local_dir.mkdir(parents=True, exist_ok=True)
    gb_dir = local_dir / "genbank"
    gb_dir.mkdir(parents=True, exist_ok=True)

    max_per_q = int(ds.get("max_records_per_query", 200))
    # Deduplicate entries by accession to avoid manifest bloat when queries overlap.
    # Also preserve previously recorded accessions so re-running with new queries does not shrink the manifest.
    out_by_acc: dict[str, dict[str, Any]] = {}
    for e in ds.get("genbank_files", []) or []:
        acc = (e or {}).get("accession")
        if acc:
            out_by_acc[str(acc)] = dict(e)
    retrieved_at = utc_now_iso()

    for q in ds.get("queries", []):
        qid = q["id"]
        db = q.get("db", "nuccore")
        term = q["term"]
        ids = _eutils_esearch(db=db, term=term, retmax=max_per_q, verify_ssl=verify_ssl)
        (local_dir / f"esearch_{qid}.json").write_text(
            json.dumps({"db": db, "term": term, "ids": ids}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # First, use esummary to map nuccore uids -> accessionversion, and only efetch missing records.
        summary_chunk = 200
        efetch_chunk = 20
        for i in range(0, len(ids), summary_chunk):
            uids = ids[i : i + summary_chunk]
            uid_to_acc = _eutils_esummary_accessionversions(db=db, ids=uids, verify_ssl=verify_ssl)

            need_fetch: list[str] = []
            for uid in uids:
                acc = uid_to_acc.get(str(uid))
                if not acc:
                    need_fetch.append(uid)
                    continue
                path = gb_dir / f"{acc}.gb"
                if path.exists():
                    if acc not in out_by_acc:
                        out_by_acc[acc] = {
                            "query": qid,
                            "db": db,
                            "accession": acc,
                            "local_path": str(path.relative_to(root_dir())),
                            "bytes": path.stat().st_size,
                            "sha256": sha256_file(path),
                            "retrieved_at_utc": retrieved_at,
                        }
                    continue
                need_fetch.append(uid)

            for j in range(0, len(need_fetch), efetch_chunk):
                chunk = need_fetch[j : j + efetch_chunk]
                gb_text = _eutils_efetch_genbank(db=db, ids=chunk, verify_ssl=verify_ssl)
                recs = _split_genbank_records(gb_text)
                for rec in recs:
                    acc = _genbank_accession(rec)
                    if not acc:
                        continue
                    path = gb_dir / f"{acc}.gb"
                    if not path.exists():
                        path.write_text(rec, encoding="utf-8")
                    if acc not in out_by_acc:
                        out_by_acc[acc] = {
                            "query": qid,
                            "db": db,
                            "accession": acc,
                            "local_path": str(path.relative_to(root_dir())),
                            "bytes": path.stat().st_size,
                            "sha256": sha256_file(path),
                            "retrieved_at_utc": retrieved_at,
                        }

    ds["genbank_files"] = [out_by_acc[k] for k in sorted(out_by_acc)]
    ds["retrieved_at_utc"] = retrieved_at


def _has_local_data(dataset: str) -> bool:
    d = data_root()

    if dataset in ("gc_prt", "all"):
        if not (d / "gc.prt").exists():
            return False

    if dataset in ("refseq_hsapiens_mrna", "all"):
        ref = d / "refseq_hsapiens_mrna"
        if not ref.exists():
            return False
        if not any(ref.glob("human.*.rna.fna.gz")):
            return False

    if dataset in ("recoding_genbank", "all"):
        gb = d / "recoding_genbank" / "genbank"
        if not gb.exists():
            return False
        if not any(gb.glob("*.gb")):
            return False

    return True


def _release_asset_url(tag: str, asset_name: str) -> str:
    if tag == "latest":
        return f"https://github.com/{DEFAULT_GITHUB_REPO}/releases/latest/download/{asset_name}"
    return f"https://github.com/{DEFAULT_GITHUB_REPO}/releases/download/{tag}/{asset_name}"


def _try_fetch_release_meta(*, tag: str, verify_ssl: bool) -> dict[str, Any] | None:
    url = _release_asset_url(tag, DEFAULT_GITHUB_RELEASE_META_NAME)
    try:
        txt = _download_text(url, timeout_s=60.0, verify_ssl=verify_ssl, retries=3, retry_sleep_s=1.0)
        obj = json.loads(txt)
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:  # noqa: BLE001 - best-effort metadata fetch
        return None


def _http_head(url: str, *, verify_ssl: bool) -> dict[str, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "the-omega-genetic-code/1.0"})
    with urllib.request.urlopen(req, timeout=60.0, context=ssl_context(verify=verify_ssl)) as r:
        return {k: v for (k, v) in (r.headers.items() if r.headers else [])}


def _is_within_directory(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def _extract_tar_gz(archive: Path, *, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_resolved = dst_dir.resolve()

    with tarfile.open(archive, mode="r:gz") as tf:
        members = tf.getmembers()
        if not members:
            raise ValueError(f"Empty archive: {archive}")

        has_data_prefix = any(m.name == "data" or m.name.startswith("data/") for m in members)
        if not has_data_prefix:
            raise ValueError(f"Unexpected archive layout (missing data/ prefix): {archive}")

        for m in members:
            if m.issym() or m.islnk():
                raise ValueError(f"Refuse to extract symlinks from archive: {m.name}")
            name = m.name
            if not name or name.startswith("/") or name.startswith("\\"):
                raise ValueError(f"Refuse to extract absolute path from archive: {name}")

            target_path = (dst_resolved / name).resolve()
            if not _is_within_directory(dst_resolved, target_path):
                raise ValueError(f"Refuse to extract path outside destination: {name}")

            tf.extract(m, path=dst_resolved)


def ensure_data_from_github_release(
    *,
    tag: str,
    dataset: str,
    verify_ssl: bool,
    force: bool = False,
) -> bool:
    """
    Ensure local data/ exists by downloading and extracting a GitHub Release asset.
    Returns True if extraction happened, False if skipped (already present).
    """
    cache_dir = data_root() / "_release_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    state_path = cache_dir / f"release_state_{dataset}.json"
    state: dict[str, Any] = {}
    if state_path.exists():
        try:
            state = read_json(state_path)
        except Exception:  # noqa: BLE001 - treat as missing state
            state = {}

    archive_url = _release_asset_url(tag, DEFAULT_GITHUB_RELEASE_ASSET_NAME)
    meta = _try_fetch_release_meta(tag=tag, verify_ssl=verify_ssl)

    desired_archive_sha256: str | None = None
    desired_archive_etag: str | None = None
    if meta and isinstance(meta.get("archive_sha256"), str):
        desired_archive_sha256 = str(meta["archive_sha256"])
    else:
        # Fall back to pinned SHAs for historical tags.
        desired_archive_sha256 = _KNOWN_RELEASE_SHA256.get(tag)
        if desired_archive_sha256 is None:
            # Best-effort update detection via HEAD/ETag.
            try:
                hdr = _http_head(archive_url, verify_ssl=verify_ssl)
                # Case-insensitive header lookup.
                for k, v in hdr.items():
                    if k.lower() == "etag":
                        desired_archive_etag = v
                        break
            except Exception:  # noqa: BLE001 - best-effort
                desired_archive_etag = None

    # Fast-path: if local manifest matches the release meta, treat local data as already up-to-date
    # without downloading the archive again.
    if (not force) and _has_local_data(dataset) and meta and isinstance(meta.get("manifest_sha256"), str):
        mp = manifest_path()
        if mp.exists():
            try:
                local_manifest_sha = sha256_file(mp)
            except Exception:  # noqa: BLE001 - treat as mismatch
                local_manifest_sha = None
            if local_manifest_sha and local_manifest_sha == str(meta["manifest_sha256"]):
                state_out: dict[str, Any] = {
                    "dataset": dataset,
                    "tag_requested": tag,
                    "archive_name": DEFAULT_GITHUB_RELEASE_ASSET_NAME,
                    "archive_url": archive_url,
                    "archive_sha256": desired_archive_sha256,
                    "archive_etag": desired_archive_etag,
                    "meta_url": _release_asset_url(tag, DEFAULT_GITHUB_RELEASE_META_NAME),
                    "meta": meta,
                    "applied_at_utc": utc_now_iso(),
                }
                write_json(state_path, state_out)
                return False

    # Skip if local data is present and state matches the remote version.
    if (not force) and _has_local_data(dataset):
        if desired_archive_sha256 and state.get("archive_sha256") == desired_archive_sha256:
            return False
        if desired_archive_etag and state.get("archive_etag") == desired_archive_etag:
            return False

    # Choose a cache filename that changes when the remote version changes.
    if desired_archive_sha256:
        archive = cache_dir / f"{desired_archive_sha256}-{DEFAULT_GITHUB_RELEASE_ASSET_NAME}"
        _ = download_file(
            archive_url,
            archive,
            expected_sha256=desired_archive_sha256,
            timeout_s=900.0,
            retries=5,
            retry_sleep_s=5.0,
            verify_ssl=verify_ssl,
        )
        actual_sha256 = desired_archive_sha256
    elif desired_archive_etag:
        etag_key = re.sub(r"[^A-Za-z0-9_.-]+", "", desired_archive_etag.strip('"'))[:64] or "etag"
        archive = cache_dir / f"etag-{etag_key}-{DEFAULT_GITHUB_RELEASE_ASSET_NAME}"
        res = download_file(
            archive_url,
            archive,
            timeout_s=900.0,
            retries=5,
            retry_sleep_s=5.0,
            verify_ssl=verify_ssl,
        )
        actual_sha256 = res.sha256
    else:
        # Last resort: always download to a timestamped path when forcing or when data is missing.
        if (not force) and _has_local_data(dataset):
            return False
        stamp = utc_now_iso().replace(":", "").replace("-", "")
        archive = cache_dir / f"{stamp}-{DEFAULT_GITHUB_RELEASE_ASSET_NAME}"
        res = download_file(
            archive_url,
            archive,
            timeout_s=900.0,
            retries=5,
            retry_sleep_s=5.0,
            verify_ssl=verify_ssl,
        )
        actual_sha256 = res.sha256

    _extract_tar_gz(archive, dst_dir=root_dir())

    # Persist state so future runs can skip when already up-to-date.
    state_out: dict[str, Any] = {
        "dataset": dataset,
        "tag_requested": tag,
        "archive_name": DEFAULT_GITHUB_RELEASE_ASSET_NAME,
        "archive_url": archive_url,
        "archive_sha256": actual_sha256,
        "archive_etag": desired_archive_etag,
        "meta_url": _release_asset_url(tag, DEFAULT_GITHUB_RELEASE_META_NAME),
        "meta": meta,
        "applied_at_utc": utc_now_iso(),
    }
    write_json(state_path, state_out)
    return True


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch datasets in data/manifest.json")
    p.add_argument(
        "--dataset",
        choices=("gc_prt", "refseq_hsapiens_mrna", "recoding_genbank", "all"),
        default="all",
        help="Which dataset group to fetch.",
    )
    p.add_argument(
        "--sync-ncbi",
        action="store_true",
        help="Fetch from upstream sources (NCBI) and update manifest checksums even if local data already exists.",
    )
    p.add_argument(
        "--no-release",
        action="store_true",
        help="Do not attempt to download the prepacked dataset from GitHub Release.",
    )
    p.add_argument(
        "--release-tag",
        default=DEFAULT_GITHUB_RELEASE_TAG,
        help=f"GitHub Release tag to use (default: {DEFAULT_GITHUB_RELEASE_TAG}).",
    )
    p.add_argument(
        "--force-release",
        action="store_true",
        help="Force re-download + re-extract of the GitHub Release asset.",
    )
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for HTTPS downloads (use only if required by your environment).",
    )
    args = p.parse_args()

    dataset = str(args.dataset)
    verify_ssl = not bool(args.insecure)

    # Preferred path: keep local data synchronized with the GitHub Release bundle.
    extracted = False
    if not bool(args.no_release):
        extracted = ensure_data_from_github_release(
            tag=str(args.release_tag),
            dataset=dataset,
            verify_ssl=verify_ssl,
            force=bool(args.force_release),
        )

    # If we have local data and the user did not request an upstream refresh, we are done.
    if _has_local_data(dataset) and (not bool(args.sync_ncbi)):
        if extracted:
            print("Dataset restored from GitHub Release into:", data_root())
        else:
            print("Dataset already present at:", data_root())
        return

    # Upstream sync path: requires manifest.json.
    mp = manifest_path()
    if not mp.exists():
        raise SystemExit(
            f"Missing manifest.json at {mp}. Either download the GitHub Release data bundle "
            f"(default: {DEFAULT_GITHUB_RELEASE_TAG}) or provide the data directory manually."
        )
    m = read_json(mp)

    if dataset in ("gc_prt", "all"):
        fetch_gc_prt(m, verify_ssl=verify_ssl)
    if dataset in ("refseq_hsapiens_mrna", "all"):
        fetch_refseq_hsapiens_mrna(m, verify_ssl=verify_ssl)
    if dataset in ("recoding_genbank", "all"):
        fetch_recoding_genbank(m, verify_ssl=verify_ssl)

    write_json(mp, m)
    print("Updated manifest:", mp)


if __name__ == "__main__":
    main()


