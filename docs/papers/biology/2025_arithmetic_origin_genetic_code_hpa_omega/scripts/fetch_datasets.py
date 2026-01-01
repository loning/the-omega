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
from progress_tools import Heartbeat


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


def _strip_dot_slash(path: str) -> str:
    while path.startswith("./"):
        path = path[2:]
    return path


def fetch_refseq_dir_dataset(ds: dict[str, Any], *, verify_ssl: bool) -> None:
    base_url = str(ds["base_url"]).rstrip("/") + "/"
    index_url = base_url + str(ds["index_file"])
    include_re = re.compile(str(ds["include_regex"]))

    local_dir = _abs_path(str(ds["local_dir"]))
    local_dir.mkdir(parents=True, exist_ok=True)

    index_text = _download_text(index_url, timeout_s=120.0, verify_ssl=verify_ssl)
    names: list[str] = []
    md5_map: dict[str, str] = {}
    for line in index_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        md5 = parts[0]
        name = _strip_dot_slash(parts[-1])
        if include_re.match(name):
            names.append(name)
            md5_map[name] = md5

    names = sorted(set(names))
    files_out: list[dict[str, Any]] = []
    for name in names:
        url = base_url + name
        dst = local_dir / name
        dst.parent.mkdir(parents=True, exist_ok=True)
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


def _parse_assembly_summary(text: str) -> list[dict[str, str]]:
    header: list[str] = []
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line:
            continue
        if line.startswith("#"):
            if "assembly_accession" in line and "\t" in line:
                header = line.lstrip("#").strip().split("\t")
            continue
        if not header:
            continue
        parts = line.split("\t")
        if len(parts) < len(header):
            continue
        row = {header[i]: parts[i] for i in range(len(header))}
        rows.append(row)
    return rows


def _parse_date_key(s: str) -> int:
    s = s.strip()
    if not s or s.lower() == "na":
        return 0
    parts = re.split(r"[/\\-\\.]+", s)
    if len(parts) < 3:
        return 0
    try:
        y = int(parts[0])
        m = int(parts[1])
        d = int(parts[2])
    except ValueError:
        return 0
    if y <= 0 or m <= 0 or d <= 0:
        return 0
    return y * 10000 + m * 100 + d


def _assembly_row_rank(row: dict[str, str]) -> tuple[int, int, int, str]:
    vs = (row.get("version_status") or "").strip().lower()
    r_latest = 0 if vs == "latest" else 1
    rc = (row.get("refseq_category") or "").strip().lower()
    if rc == "reference genome":
        r_ref = 0
    elif rc == "representative genome":
        r_ref = 1
    else:
        r_ref = 2
    date_key = 0
    for k in ("seq_rel_date", "release_date"):
        date_key = max(date_key, _parse_date_key(row.get(k) or ""))
    # Prefer larger date_key -> smaller negative.
    return (r_latest, r_ref, -date_key, row.get("assembly_accession") or "")


def _normalize_ftp_url(p: str) -> str:
    p = p.strip()
    if p.startswith("ftp://"):
        return "https://" + p[len("ftp://") :]
    return p


def fetch_refseq_assembly_files(ds: dict[str, Any], *, verify_ssl: bool) -> None:
    summary_url = str(ds["assembly_summary_url"])
    txt = _download_text(summary_url, timeout_s=120.0, verify_ssl=verify_ssl, retries=6, retry_sleep_s=2.0)
    rows = _parse_assembly_summary(txt)
    if not rows:
        raise SystemExit(f"Failed to parse any assemblies from: {summary_url}")

    filters = dict(ds.get("filters", {}) or {})
    want_level = (filters.get("assembly_level") or "").strip()
    want_refcat = (filters.get("refseq_category") or "").strip()
    want_org_sub = (filters.get("organism_contains") or "").strip().lower()

    candidates: list[dict[str, str]] = []
    for r in rows:
        if want_level:
            if (r.get("assembly_level") or "").strip() != want_level:
                continue
        if want_refcat:
            if (r.get("refseq_category") or "").strip() != want_refcat:
                continue
        if want_org_sub:
            org = (r.get("organism_name") or "").strip().lower()
            if want_org_sub not in org:
                continue
        ftp_path = (r.get("ftp_path") or "").strip()
        if not ftp_path or ftp_path.lower() == "na":
            continue
        candidates.append(r)

    if not candidates:
        raise SystemExit(f"No assembly_summary rows matched filters for dataset local_dir={ds.get('local_dir')}")

    chosen = min(candidates, key=_assembly_row_rank)
    ftp_base = _normalize_ftp_url(chosen["ftp_path"]).rstrip("/")

    md5_url = ftp_base + "/md5checksums.txt"
    md5_text = _download_text(md5_url, timeout_s=120.0, verify_ssl=verify_ssl, retries=6, retry_sleep_s=2.0)
    md5_map: dict[str, str] = {}
    names: list[str] = []
    for line in md5_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        md5 = parts[0]
        name = _strip_dot_slash(parts[-1])
        # Ignore directory entries.
        if not name or name.endswith("/"):
            continue
        md5_map[name] = md5
        names.append(name)

    wanted_suffixes = [str(x) for x in (ds.get("wanted_files", []) or [])]
    if not wanted_suffixes:
        raise SystemExit(f"Dataset has no wanted_files: local_dir={ds.get('local_dir')}")

    local_dir = _abs_path(str(ds["local_dir"]))
    local_dir.mkdir(parents=True, exist_ok=True)

    files_out: list[dict[str, Any]] = []
    for suffix in wanted_suffixes:
        matches = sorted({n for n in names if n.endswith(suffix)})
        if not matches:
            raise SystemExit(f"Missing wanted file '{suffix}' under {ftp_base}")
        rel_name = matches[0]
        url = ftp_base + "/" + rel_name
        dst = local_dir / Path(rel_name).name
        res = download_file(
            url,
            dst,
            verify_ssl=verify_ssl,
            timeout_s=900.0,
            retries=6,
            retry_sleep_s=5.0,
        )
        files_out.append(
            {
                "name": Path(rel_name).name,
                "url": url,
                "bytes": res.bytes,
                "sha256": res.sha256,
                "retrieved_at_utc": res.retrieved_at_utc,
                "ncbi_md5": md5_map.get(rel_name),
            }
        )

    ds["selected_assembly"] = {
        "assembly_accession": chosen.get("assembly_accession"),
        "asm_name": chosen.get("asm_name"),
        "organism_name": chosen.get("organism_name"),
        "taxid": chosen.get("taxid"),
        "assembly_level": chosen.get("assembly_level"),
        "refseq_category": chosen.get("refseq_category"),
        "version_status": chosen.get("version_status"),
        "seq_rel_date": chosen.get("seq_rel_date"),
        "release_date": chosen.get("release_date"),
        "ftp_path": ftp_base,
        "md5checksums_url": md5_url,
    }
    ds["files"] = files_out
    ds["retrieved_at_utc"] = utc_now_iso()


def fetch_refseq_hsapiens_mrna(m: dict[str, Any], *, verify_ssl: bool) -> None:
    ds = m["datasets"]["refseq_hsapiens_mrna"]
    fetch_refseq_dir_dataset(ds, verify_ssl=verify_ssl)


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


def fetch_recoding_genbank(m: dict[str, Any], *, verify_ssl: bool, heartbeat_s: float = 60.0) -> None:
    ds = m["datasets"]["ncbi_recoding_genbank"]
    local_dir = _abs_path(ds["local_dir"])
    local_dir.mkdir(parents=True, exist_ok=True)
    gb_dir = local_dir / "genbank"
    gb_dir.mkdir(parents=True, exist_ok=True)

    max_per_q = int(ds.get("max_records_per_query", 200))
    hb_all = Heartbeat(every_s=float(heartbeat_s), prefix="[progress] fetch_recoding_genbank")
    hb_all.force(f"start queries={len(ds.get('queries', []) or [])} max_records_per_query={max_per_q}")
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
        hb = Heartbeat(every_s=float(heartbeat_s), prefix=f"[progress] fetch_recoding_genbank:{qid}")
        hb.force("esearch")
        ids = _eutils_esearch(db=db, term=term, retmax=max_per_q, verify_ssl=verify_ssl)
        hb.force(f"esearch ids={len(ids)}")
        (local_dir / f"esearch_{qid}.json").write_text(
            json.dumps({"db": db, "term": term, "ids": ids}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # First, use esummary to map nuccore uids -> accessionversion, and only efetch missing records.
        summary_chunk = 200
        efetch_chunk = 20
        uids_total = int(len(ids))
        uids_processed = 0
        n_existing = 0
        n_need_fetch = 0
        n_new_records = 0
        n_uids_no_acc = 0
        for i in range(0, len(ids), summary_chunk):
            uids = ids[i : i + summary_chunk]
            uids_processed += int(len(uids))
            uid_to_acc = _eutils_esummary_accessionversions(db=db, ids=uids, verify_ssl=verify_ssl)

            need_fetch: list[str] = []
            for uid in uids:
                acc = uid_to_acc.get(str(uid))
                if not acc:
                    n_uids_no_acc += 1
                    need_fetch.append(uid)
                    continue
                path = gb_dir / f"{acc}.gb"
                if path.exists():
                    n_existing += 1
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
                n_need_fetch += 1
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
                        n_new_records += 1
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
                hb.maybe(
                    f"uids={uids_processed}/{uids_total} existing={n_existing} need_fetch={n_need_fetch} "
                    f"new_records={n_new_records} manifest_acc={len(out_by_acc)}"
                )
            hb.maybe(
                f"uids={uids_processed}/{uids_total} existing={n_existing} need_fetch={n_need_fetch} "
                f"new_records={n_new_records} uids_no_acc={n_uids_no_acc} manifest_acc={len(out_by_acc)}"
            )

        hb.force(
            f"done ids={uids_total} existing={n_existing} need_fetch={n_need_fetch} "
            f"new_records={n_new_records} uids_no_acc={n_uids_no_acc} manifest_acc={len(out_by_acc)}"
        )

    ds["genbank_files"] = [out_by_acc[k] for k in sorted(out_by_acc)]
    ds["retrieved_at_utc"] = retrieved_at


def _resolve_dataset_keys(m: dict[str, Any], dataset: str) -> list[str]:
    d = str(dataset).strip()
    if not d:
        raise SystemExit("--dataset must be non-empty")
    datasets = (m.get("datasets") or {}) if isinstance(m.get("datasets"), dict) else {}
    panels = (m.get("panels") or {}) if isinstance(m.get("panels"), dict) else {}

    aliases = {
        "gc_prt": ["ncbi_gc_prt"],
        "recoding_genbank": ["ncbi_recoding_genbank"],
    }
    if d in aliases:
        return aliases[d]

    if d == "all":
        return sorted(str(k) for k in datasets.keys())

    if d == "refseq_panel":
        p = panels.get("corpus_panel_v1") or {}
        items = p.get("items", []) or []
        keys = sorted({str(x.get("dataset")) for x in items if isinstance(x, dict) and x.get("dataset")})
        if not keys:
            raise SystemExit("manifest.panels.corpus_panel_v1.items is empty; cannot resolve refseq_panel")
        return keys

    if d == "nonstandard_examples":
        p = panels.get("nonstandard_examples_v1") or {}
        items = p.get("items", []) or []
        keys = sorted({str(x.get("dataset")) for x in items if isinstance(x, dict) and x.get("dataset")})
        if not keys:
            raise SystemExit("manifest.panels.nonstandard_examples_v1.items is empty; cannot resolve nonstandard_examples")
        return keys

    # Dataset key directly.
    if d in datasets:
        return [d]
    if d in ("refseq_hsapiens_mrna",):
        return [d]

    raise SystemExit(f"Unknown dataset selector: {d}")


def _is_dataset_present(m: dict[str, Any] | None, dataset_key: str) -> bool:
    droot = data_root()
    key = str(dataset_key)
    if key == "ncbi_gc_prt":
        return (droot / "gc.prt").exists()
    if key == "ncbi_recoding_genbank":
        gb = droot / "recoding_genbank" / "genbank"
        return gb.exists() and any(gb.glob("*.gb"))

    if not m or not isinstance(m.get("datasets"), dict):
        return False
    ds = (m["datasets"] or {}).get(key)
    if not isinstance(ds, dict):
        return False

    # Generic local_path presence (best-effort).
    lp = ds.get("local_path")
    if isinstance(lp, str):
        p = _abs_path(lp)
        if p.exists():
            return True

    t = str(ds.get("type") or "")
    if t == "ncbi_refseq_dir":
        local_dir = ds.get("local_dir")
        include_regex = ds.get("include_regex")
        if not isinstance(local_dir, str) or not isinstance(include_regex, str):
            return False
        base = _abs_path(local_dir)
        if not base.exists():
            return False
        try:
            r = re.compile(include_regex)
        except re.error:
            return any(base.glob("*.gz"))
        return any(r.match(fp.name) for fp in base.iterdir() if fp.is_file())

    if t == "ncbi_refseq_assembly_files":
        local_dir = ds.get("local_dir")
        wanted = ds.get("wanted_files")
        if not isinstance(local_dir, str):
            return False
        base = _abs_path(local_dir)
        if not base.exists():
            return False
        wanted_suffixes = [str(x) for x in (wanted or [])]
        if not wanted_suffixes:
            return any(base.iterdir())
        for suf in wanted_suffixes:
            if not any(fp.is_file() and fp.name.endswith(suf) for fp in base.iterdir()):
                return False
        return True

    return False


def _has_local_data(dataset: str) -> bool:
    d = data_root()
    mp = manifest_path()
    m: dict[str, Any] | None = None
    if mp.exists():
        try:
            m = read_json(mp)
        except Exception:  # noqa: BLE001
            m = None

    # Without a manifest, fall back to legacy checks.
    if m is None:
        if dataset in ("gc_prt", "all") and not (d / "gc.prt").exists():
            return False
        if dataset in ("refseq_hsapiens_mrna", "all"):
            ref = d / "refseq_hsapiens_mrna"
            if (not ref.exists()) or (not any(ref.glob("human.*.rna.fna.gz"))):
                return False
        if dataset in ("recoding_genbank", "all"):
            gb = d / "recoding_genbank" / "genbank"
            if (not gb.exists()) or (not any(gb.glob("*.gb"))):
                return False
        return True

    try:
        keys = _resolve_dataset_keys(m, dataset)
    except SystemExit:
        # Unknown selector: treat as missing.
        return False
    return all(_is_dataset_present(m, k) for k in keys)


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
        default="all",
        help=(
            "Dataset selector: gc_prt, recoding_genbank, refseq_hsapiens_mrna, "
            "refseq_panel, nonstandard_examples, all, or a dataset key from manifest.datasets."
        ),
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
    p.add_argument(
        "--heartbeat-s",
        type=float,
        default=60.0,
        help="Emit a progress heartbeat at least once per this many seconds (0 disables).",
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
    keys = _resolve_dataset_keys(m, dataset)
    for k in keys:
        if k == "ncbi_gc_prt":
            fetch_gc_prt(m, verify_ssl=verify_ssl)
            continue
        if k == "ncbi_recoding_genbank":
            fetch_recoding_genbank(m, verify_ssl=verify_ssl, heartbeat_s=float(args.heartbeat_s))
            continue

        ds = m["datasets"].get(k)
        if not isinstance(ds, dict):
            raise SystemExit(f"Missing dataset in manifest: {k}")
        t = str(ds.get("type") or "")
        if t == "ncbi_refseq_dir":
            fetch_refseq_dir_dataset(ds, verify_ssl=verify_ssl)
        elif t == "ncbi_refseq_assembly_files":
            fetch_refseq_assembly_files(ds, verify_ssl=verify_ssl)
        else:
            # Some manifest entries are informational or local-only (e.g., small case-study FASTA files).
            # Leave them untouched.
            continue

    write_json(mp, m)
    print("Updated manifest:", mp)


if __name__ == "__main__":
    main()


