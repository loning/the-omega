# -*- coding: utf-8 -*-
"""
Validate local artifacts for Supabase import / reproducibility checks.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from provenance_tools import infer_analysis_version


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


def _iter_jsonl_dicts(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise SystemExit(f"Invalid JSON at {path}:{line_no}") from e
            if not isinstance(obj, dict):
                continue
            yield line_no, obj


def _as_pos_int(x: object) -> int | None:
    try:
        v = int(x)  # type: ignore[arg-type]
    except Exception:
        return None
    return v if v > 0 else None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate local artifacts used by Supabase import scripts.")
    p.add_argument(
        "--recoding-jsonl",
        default="data/recoding_genbank/recoding_sites.jsonl",
        help="Recoding JSONL path (relative to project root by default).",
    )
    p.add_argument(
        "--recoding-summary-json",
        default="data/recoding_genbank/recoding_sites_summary.json",
        help="Recoding summary JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--refseq-summary-json",
        default="data/refseq_hsapiens_mrna/transcriptome_summary.json",
        help="RefSeq merged transcriptome summary JSON path (relative to project root by default).",
    )
    p.add_argument("--no-recoding", action="store_true", help="Skip recoding JSONL + summary checks.")
    p.add_argument("--no-refseq", action="store_true", help="Skip RefSeq transcriptome summary checks.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = root_dir()

    rec_jsonl = (root / str(args.recoding_jsonl)).resolve()
    rec_sum = (root / str(args.recoding_summary_json)).resolve()
    ref_sum = (root / str(args.refseq_summary_json)).resolve()

    if not args.no_recoding:
        if not rec_jsonl.exists():
            raise SystemExit(f"Missing recoding JSONL: {rec_jsonl}")
        if not rec_sum.exists():
            raise SystemExit(f"Missing recoding summary JSON: {rec_sum}")
    if not args.no_refseq:
        if not ref_sum.exists():
            raise SystemExit(f"Missing RefSeq transcriptome summary JSON: {ref_sum}")

    # ---- RefSeq transcriptome summary ----
    ref_schema_v: int | None = None
    ref_av: int | None = None
    ref_k: int | None = None
    n_schemes = 0
    if not args.no_refseq:
        ref_obj = _read_json_dict(ref_sum, label="transcriptome_summary.json")
        ref_schema_v = _as_pos_int(ref_obj.get("schema_version"))
        if ref_schema_v is None:
            raise SystemExit(f"Missing/invalid schema_version in {ref_sum}")
        ref_av = infer_analysis_version(ref_sum, summary_obj=ref_obj)
        if not ref_av:
            raise SystemExit(f"Missing/invalid analysis_version for {ref_sum} (check .meta.json sidecar)")
        ref_k = _as_pos_int(ref_obj.get("stop_window"))
        if ref_k is None:
            raise SystemExit(f"Missing/invalid stop_window in {ref_sum}")
        comp = ref_obj.get("stop_context_composition")
        if int(ref_schema_v) >= 3:
            if not isinstance(comp, dict) or not comp:
                raise SystemExit(f"Missing/invalid stop_context_composition in {ref_sum}")
            comp_schemes = comp.get("schemes") if isinstance(comp.get("schemes"), dict) else None
            n_schemes = len(comp_schemes) if isinstance(comp_schemes, dict) else 0
        else:
            # Back-compat: older schema versions may not include composition-adjusted controls.
            if isinstance(comp, dict) and comp:
                comp_schemes = comp.get("schemes") if isinstance(comp.get("schemes"), dict) else None
                n_schemes = len(comp_schemes) if isinstance(comp_schemes, dict) else 0

    # ---- Recoding summary ----
    rec_schema_v: int | None = None
    rec_av: int | None = None
    if not args.no_recoding:
        rec_obj = _read_json_dict(rec_sum, label="recoding_sites_summary.json")
        rec_schema_v = _as_pos_int(rec_obj.get("schema_version"))
        if rec_schema_v is None:
            raise SystemExit(f"Missing/invalid schema_version in {rec_sum}")
        rec_av = infer_analysis_version(rec_sum, summary_obj=rec_obj)
        if not rec_av:
            raise SystemExit(f"Missing/invalid analysis_version in {rec_sum} (check .meta.json sidecar)")

    # ---- Recoding JSONL ----
    jsonl_av: int | None = None
    k_values: list[int] = []
    n_rows = 0
    if not args.no_recoding:
        av_set: set[int] = set()
        k_set: set[int] = set()
        key_set: set[tuple[int, int, str, int]] = set()
        for line_no, row in _iter_jsonl_dicts(rec_jsonl):
            av = _as_pos_int(row.get("analysis_version"))
            if av is None:
                raise SystemExit(f"Missing/invalid analysis_version at {rec_jsonl}:{line_no}")
            k = _as_pos_int(row.get("k"))
            if k is None:
                raise SystemExit(f"Missing/invalid k at {rec_jsonl}:{line_no}")
            ver = row.get("version")
            if not isinstance(ver, str) or not ver.strip():
                raise SystemExit(f"Missing/invalid version at {rec_jsonl}:{line_no}")
            try:
                pos_start = int(row.get("pos_start"))  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Missing/invalid pos_start at {rec_jsonl}:{line_no}") from e

            av_set.add(int(av))
            k_set.add(int(k))
            key = (int(av), int(k), str(ver), int(pos_start))
            if key in key_set:
                raise SystemExit(f"Duplicate conflict key in JSONL at {rec_jsonl}:{line_no}: {key}")
            key_set.add(key)
            n_rows += 1

        if n_rows <= 0:
            raise SystemExit(f"No rows found in JSONL: {rec_jsonl}")
        if len(av_set) != 1:
            raise SystemExit(f"Expected a single analysis_version in JSONL, got: {sorted(av_set)[:10]}")
        jsonl_av = next(iter(av_set))
        if rec_av is not None and int(jsonl_av) != int(rec_av):
            raise SystemExit(f"analysis_version mismatch: JSONL={jsonl_av} vs summary={rec_av}")
        k_values = sorted(k_set)

    print("OK")
    if not args.no_refseq:
        print(f"RefSeq transcriptome_summary: schema_v={ref_schema_v} analysis_v={ref_av} k={ref_k} comp_schemes={n_schemes}")
    if not args.no_recoding:
        print(f"Recoding summary: schema_v={rec_schema_v} analysis_v={rec_av}")
        print(f"Recoding JSONL: rows={n_rows} analysis_v={jsonl_av} k_values={k_values}")


if __name__ == "__main__":
    main()


