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
from pathlib import Path
from typing import Any

from data_manager import download_file, read_json, sha256_file, ssl_context, utc_now_iso, write_json


DEFAULT_GITHUB_RELEASE_TAG = "genetic-code-data-v1.0"
DEFAULT_GITHUB_RELEASE_ASSET_NAME = "genetic-code-data.tar.gz"
DEFAULT_GITHUB_RELEASE_URL = (
    f"https://github.com/loning/the-omega/releases/download/{DEFAULT_GITHUB_RELEASE_TAG}/{DEFAULT_GITHUB_RELEASE_ASSET_NAME}"
)
_KNOWN_RELEASE_SHA256: dict[str, str] = {
    DEFAULT_GITHUB_RELEASE_TAG: "53246e0563de007d85c9ec15e1991004a7ff237f966ab26eac3abb836e248ae7",
}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def manifest_path() -> Path:
    return root_dir() / "data" / "manifest.json"

def data_root() -> Path:
    return root_dir() / "data"


def _abs_path(rel: str) -> Path:
    return root_dir() / rel


def _download_text(url: str, *, timeout_s: float = 60.0, verify_ssl: bool = True) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "the-omega-genetic-code/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context(verify=verify_ssl)) as r:
        return r.read().decode("utf-8", errors="replace")


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
    q = {
        "db": db,
        "term": term,
        "retmax": str(int(retmax)),
        "retmode": "json",
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(q)
    txt = _download_text(url, timeout_s=120.0, verify_ssl=verify_ssl)
    obj = json.loads(txt)
    ids = obj.get("esearchresult", {}).get("idlist", [])
    return [str(x) for x in ids]


def _eutils_efetch_genbank(db: str, ids: list[str], *, verify_ssl: bool) -> str:
    # Use comma-separated ids; chunking handled by caller.
    q = {
        "db": db,
        "id": ",".join(ids),
        "rettype": "gb",
        "retmode": "text",
    }
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(q)
    return _download_text(url, timeout_s=240.0, verify_ssl=verify_ssl)


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
    out_files: list[dict[str, Any]] = []
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

        # Fetch GenBank records in chunks.
        chunk_size = 50
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            gb_text = _eutils_efetch_genbank(db=db, ids=chunk, verify_ssl=verify_ssl)
            recs = _split_genbank_records(gb_text)
            for rec in recs:
                acc = _genbank_accession(rec)
                if not acc:
                    continue
                path = gb_dir / f"{acc}.gb"
                path.write_text(rec, encoding="utf-8")
                out_files.append(
                    {
                        "query": qid,
                        "db": db,
                        "accession": acc,
                        "local_path": str(path.relative_to(root_dir())),
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                        "retrieved_at_utc": retrieved_at,
                    }
                )

    ds["genbank_files"] = out_files
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


def _release_url(tag: str) -> str:
    return f"https://github.com/loning/the-omega/releases/download/{tag}/{DEFAULT_GITHUB_RELEASE_ASSET_NAME}"


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
    if (not force) and _has_local_data(dataset):
        return False

    url = _release_url(tag)
    expected_sha256 = _KNOWN_RELEASE_SHA256.get(tag)

    cache_dir = data_root() / "_release_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = cache_dir / f"{tag}-{DEFAULT_GITHUB_RELEASE_ASSET_NAME}"

    _ = download_file(url, archive, expected_sha256=expected_sha256, timeout_s=900.0, retries=5, retry_sleep_s=5.0, verify_ssl=verify_ssl)
    _extract_tar_gz(archive, dst_dir=root_dir())
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

    # Preferred path: if data is missing, download the packed dataset from GitHub Release.
    extracted = False
    if (not bool(args.no_release)) and ((not _has_local_data(dataset)) or bool(args.force_release)):
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
            f"(default tag: {DEFAULT_GITHUB_RELEASE_TAG}) or provide the data directory manually."
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


