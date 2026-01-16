# -*- coding: utf-8 -*-
"""
Fetch NCBI SRA runinfo (CSV) via Entrez eUtils.

This helper complements the GEO bigWig fetchers by enabling a raw-read pipeline
for Ribo-seq / RNA-seq datasets that only provide FASTQ via SRA.

Examples:
  python scripts/fetch_sra_runinfo.py --term SRP257547 --out data/_cache/SRP257547.runinfo.csv
  python scripts/fetch_sra_runinfo.py --term PRJNA626635 --print-summary
  python scripts/fetch_sra_runinfo.py --term SRR14517742 --print-rows 3
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return root_dir() / "data"


def cache_dir() -> Path:
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch(url: str, *, timeout_s: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        return r.read()


def _esearch_ids(term: str, *, retmax: int) -> list[str]:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=sra&term={urllib.parse.quote(term)}&retmax={int(retmax)}"
    )
    xml = _fetch(url).decode("utf-8", "ignore")
    ids = re.findall(r"<Id>(\d+)</Id>", xml)
    if not ids:
        raise SystemExit(f"No SRA IDs returned for term={term!r} (url={url})")
    return ids


def _efetch_runinfo(ids: list[str]) -> str:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=sra&id={urllib.parse.quote(','.join(ids))}&rettype=runinfo&retmode=text"
    )
    return _fetch(url).decode("utf-8", "ignore")


def fetch_runinfo_rows(term: str, *, retmax: int = 20000, chunk_size: int = 200) -> list[dict[str, str]]:
    ids = _esearch_ids(term, retmax=retmax)

    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for i in range(0, len(ids), int(chunk_size)):
        chunk = ids[i : i + int(chunk_size)]
        txt = _efetch_runinfo(chunk)
        rdr = csv.DictReader(io.StringIO(txt))
        if header is None:
            header = list(rdr.fieldnames or [])
        for r in rdr:
            rows.append({k: (r.get(k) or "") for k in (header or [])})

    if not rows:
        raise SystemExit(f"Empty runinfo for term={term!r} (ids={len(ids)})")
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = sorted({k for r in rows for k in r.keys()})
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    tmp.replace(path)


def _print_summary(rows: list[dict[str, str]]) -> None:
    def uniq(key: str) -> int:
        return len({(r.get(key) or "").strip() for r in rows if (r.get(key) or "").strip()})

    print(f"[runinfo] runs={len(rows)}", flush=True)
    for k in ["BioProject", "SRAStudy", "Experiment", "Sample", "LibraryStrategy", "Platform", "Model"]:
        if any((r.get(k) or "").strip() for r in rows):
            print(f"  {k}: {uniq(k)} unique", flush=True)


def _sanitize(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s)
    return s or "sra"


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch SRA runinfo CSV via NCBI eUtils.")
    ap.add_argument("--term", required=True, help="SRA search term (e.g., SRP..., PRJNA..., SRR..., GSM...).")
    ap.add_argument("--retmax", type=int, default=20000, help="Max SRA records to return from esearch.")
    ap.add_argument("--chunk-size", type=int, default=200, help="IDs per efetch request.")
    ap.add_argument("--out", default="", help="Output CSV path (default: data/_cache/<term>.runinfo.csv).")
    ap.add_argument("--print-summary", action="store_true", help="Print a brief summary.")
    ap.add_argument("--print-rows", type=int, default=0, help="Print the first N rows as TSV for inspection.")
    args = ap.parse_args()

    term = str(args.term).strip()
    out = Path(str(args.out)) if str(args.out).strip() else (cache_dir() / f"{_sanitize(term)}.runinfo.csv")
    if not out.is_absolute():
        out = root_dir() / out

    rows = fetch_runinfo_rows(term, retmax=int(args.retmax), chunk_size=int(args.chunk_size))
    _write_csv(out, rows)
    print(f"Wrote: {out}", flush=True)

    if args.print_summary:
        _print_summary(rows)

    n = int(args.print_rows)
    if n > 0:
        header = sorted({k for r in rows for k in r.keys()})
        print("\t".join(header), flush=True)
        for r in rows[:n]:
            print("\t".join([(r.get(k) or "") for k in header]), flush=True)


if __name__ == "__main__":
    main()

