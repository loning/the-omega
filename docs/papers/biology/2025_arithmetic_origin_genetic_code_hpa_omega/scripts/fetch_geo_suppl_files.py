# -*- coding: utf-8 -*-
"""
Fetch GEO supplementary files (generic helper).

This is a small generalization of fetch_geo_riboseq_bigwig.py:
it can list/download any supplementary files (BEDGRAPH/TAR/BIGWIG/etc.)
from a GEO Series page.

Outputs go under the paper-local data directory (ignored by git):
  data/probing/<GSE>/

Examples:
  python scripts/fetch_geo_suppl_files.py --gse GSE95465 --list
  python scripts/fetch_geo_suppl_files.py --gse GSE95465 --regex 'bedgraph'
  python scripts/fetch_geo_suppl_files.py --gse GSE95567 --file GSE95567_RAW.tar --extract --member-regex 'bedgraph'
"""

from __future__ import annotations

import argparse
import hashlib
import re
import tarfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return root_dir() / "data"


def probing_dir() -> Path:
    d = data_dir() / "probing"
    d.mkdir(parents=True, exist_ok=True)
    return d


def geo_suppl_base_url(gse: str) -> str:
    # GEO FTP layout groups by thousands:
    #   GSE148965 -> .../GSE148nnn/GSE148965/suppl/
    #   GSE95465  -> .../GSE95nnn/GSE95465/suppl/
    m = re.match(r"^GSE(\d+)$", gse)
    if not m:
        raise ValueError(f"Invalid GSE accession: {gse}")
    digits = m.group(1)
    prefix_digits = digits[:-3] if len(digits) > 3 else ""
    prefix = "GSE" + prefix_digits + "nnn"
    return f"https://ftp.ncbi.nlm.nih.gov/geo/series/{prefix}/{gse}/suppl/"


def geo_series_page_url(gse: str) -> str:
    return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={urllib.parse.quote(gse)}"


@dataclass(frozen=True)
class GeoSupplFile:
    name: str
    size_label: str
    file_type: str


def _fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def list_geo_suppl_files(gse: str) -> list[GeoSupplFile]:
    html = _fetch_html(geo_series_page_url(gse))
    files: list[GeoSupplFile] = []

    # The supplementary file table contains rows like:
    # <tr valign="top"><td>NAME</td><td>SIZE</td><td>...</td><td>TYPE</td></tr>
    row_re = re.compile(
        r'<tr\s+valign="top">\s*'
        r"<td[^>]*>([^<]+)</td>\s*"
        r"<td[^>]*>([^<]+)</td>\s*"
        r"<td[^>]*>.*?</td>\s*"
        r"<td[^>]*>([^<]+)</td>\s*"
        r"</tr>",
        re.I | re.S,
    )

    for m in row_re.finditer(html):
        name = m.group(1).strip()
        size_label = m.group(2).strip()
        file_type = m.group(3).strip()
        files.append(GeoSupplFile(name=name, size_label=size_label, file_type=file_type))

    return files


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, out_path: Path, *, force: bool) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not force:
        return
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r:
        with tmp.open("wb") as f:
            for chunk in iter(lambda: r.read(1024 * 1024), b""):
                f.write(chunk)
    tmp.replace(out_path)


def extract_tar_members(
    tar_path: Path,
    out_dir: Path,
    *,
    member_regex: re.Pattern[str] | None,
    force: bool,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    with tarfile.open(tar_path, "r:*") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            name = Path(member.name).name
            if member_regex is not None and not member_regex.search(name):
                continue
            out_path = out_dir / name
            if out_path.exists() and not force:
                extracted.append(out_path)
                continue
            with tf.extractfile(member) as src:
                if src is None:
                    continue
                tmp = out_path.with_suffix(out_path.suffix + ".tmp")
                with tmp.open("wb") as dst:
                    dst.write(src.read())
                tmp.replace(out_path)
            extracted.append(out_path)

    return extracted


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch GEO supplementary files (generic).")
    ap.add_argument("--gse", required=True, help="GEO Series accession, e.g. GSE95465.")
    ap.add_argument(
        "--file",
        dest="files",
        action="append",
        default=[],
        help="Exact supplementary filename to download (repeatable). When set, skips scraping the GEO page.",
    )
    ap.add_argument("--out-dir", default="", help="Optional override output dir (default: data/probing/<GSE>/).")
    ap.add_argument("--regex", default="", help="Optional regex to filter supplementary filenames.")
    ap.add_argument("--member-regex", default="", help="Optional regex to filter TAR members when --extract is set.")
    ap.add_argument("--list", action="store_true", help="List supplementary files and exit.")
    ap.add_argument("--extract", action="store_true", help="If downloading a tar bundle, extract members (optionally filtered).")
    ap.add_argument("--force", action="store_true", help="Re-download / re-extract even if files exist.")
    args = ap.parse_args()

    gse = str(args.gse).strip()
    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else (probing_dir() / gse)
    out_dir.mkdir(parents=True, exist_ok=True)

    rx = re.compile(str(args.regex), re.I) if str(args.regex).strip() else None
    member_rx = re.compile(str(args.member_regex), re.I) if str(args.member_regex).strip() else rx

    base = geo_suppl_base_url(gse)
    if args.list and args.files:
        for fn in args.files:
            print(fn)
        return

    if args.files:
        selected_names = [str(x).strip() for x in args.files if str(x).strip()]
    else:
        files = list_geo_suppl_files(gse)
        if args.list:
            for f in files:
                print(f"{f.name}\\t{f.size_label}\\t{f.file_type}")
            return

        selected = files
        if rx is not None:
            selected = [f for f in selected if rx.search(f.name)]
            if not selected:
                raise SystemExit(f"No supplementary files match --regex for {gse}.")
        selected_names = [f.name for f in selected]

    downloaded: list[Path] = []
    extracted: list[Path] = []

    for name in selected_names:
        url = base + urllib.parse.quote(name)
        dest = out_dir / name
        print(f"[download] {url} -> {dest}", flush=True)
        download(url, dest, force=bool(args.force))
        downloaded.append(dest)

        if args.extract and dest.suffix.lower() in {".tar", ".tgz"}:
            print(f"[extract] {dest}", flush=True)
            extracted.extend(extract_tar_members(dest, out_dir, member_regex=member_rx, force=bool(args.force)))

    for p in downloaded:
        try:
            sha = _sha256_path(p)
        except Exception:
            sha = "?"
        print(f"[ok] {p.name} sha256={sha}", flush=True)
    for p in extracted:
        try:
            sha = _sha256_path(p)
        except Exception:
            sha = "?"
        print(f"[ok] extracted {p.name} sha256={sha}", flush=True)


if __name__ == "__main__":
    main()
