# -*- coding: utf-8 -*-
"""
Sequence-level tests for nonstandard genetic codes (P3).

This script complements exp_nonstandard_codes.py (table-level) by evaluating
sequence corpora (e.g. CDS FASTA) under a specified NCBI translation table:
  - start boundary-hit enrichment (vs within-CDS background)
  - terminal-stop boundary-hit preference (vs uniform over stop set)

Inputs:
  - data/gc.prt  (NCBI translation tables)
  - datasets referenced by data/manifest.json under panels.nonstandard_examples_v1

Outputs:
  - data/nonstandard_sequence_tests.json
  - sections/generated/nonstandard_sequence_tests_summary.tex
  - sections/generated/nonstandard_sequence_tests_rows.tex

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from exp_nonstandard_codes import codons_for_table, parse_gc_prt
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, fold_codon, iter_fasta
from progress_tools import Heartbeat
from stats_tools import normal_two_sided_p


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    return root_dir() / "data"


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _read_json_dict(path: Path) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def nonstandard_item_cache_dir() -> Path:
    """
    Per-item cache for nonstandard sequence tests.

    Panel-level cache invalidates when any item changes; item-level caches prevent
    rescanning unrelated datasets.
    """
    d = data_root() / "_cache" / f"nonstandard_sequence_tests_items_v{int(ANALYSIS_VERSION)}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_manifest() -> dict[str, Any]:
    return json.loads((data_root() / "manifest.json").read_text(encoding="utf-8"))


def dataset_files_from_manifest(m: dict[str, Any], dataset_key: str) -> list[Path]:
    ds = (m.get("datasets") or {}).get(dataset_key)
    if not isinstance(ds, dict):
        raise SystemExit(f"Missing dataset in manifest: {dataset_key}")
    t = str(ds.get("type") or "")
    if t in ("ncbi_refseq_dir", "ncbi_refseq_assembly_files"):
        local_dir = root_dir() / str(ds.get("local_dir") or "")
        files = []
        for e in (ds.get("files", []) or []):
            if not isinstance(e, dict):
                continue
            name = e.get("name")
            if isinstance(name, str) and name:
                files.append(local_dir / name)
        if files:
            return files
        return sorted(local_dir.glob("*.gz"))
    lp = ds.get("local_path")
    if isinstance(lp, str) and lp:
        return [root_dir() / lp]
    return []


def fold_is_boundary(codon_rna: str) -> bool:
    if codon_rna not in GENETIC_CODE:
        return False
    return str(fold_codon(codon_rna, MU_STAR).w) in BOUNDARY_WORDS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sequence-level tests for nonstandard genetic codes (P3)")
    p.add_argument("--panel", default="nonstandard_examples_v1", help="Panel name under manifest.panels.")
    p.add_argument(
        "--out-json",
        default=str(root_dir() / "data" / "nonstandard_sequence_tests.json"),
        help="Output JSON path.",
    )
    p.add_argument("--max-records", type=int, default=0, help="Optional max records per dataset (0 = no limit).")
    p.add_argument(
        "--heartbeat-s",
        type=float,
        default=60.0,
        help="Emit a progress heartbeat at least once per this many seconds (0 disables).",
    )
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def _emit_latex_from_summary(out: dict[str, object]) -> None:
    items = out.get("items") or []
    if not isinstance(items, list):
        items = []
    def tex_path(s: object) -> str:
        t = str(s) if s is not None else ""
        if not t or t == "-":
            return "-"
        return f"\\path{{{t}}}"
    # LaTeX fragments (compact table rows).
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if not it.get("present"):
            rows.append(f"{tex_path(it.get('label','-'))} & {it.get('code_id','-')} & - & - & - & - & - \\\\")
            continue
        tests = it.get("tests") or {}
        if not isinstance(tests, dict):
            tests = {}
        st = tests.get("start_boundary") or {}
        sp = tests.get("stop_boundary") or {}
        if not isinstance(st, dict) or not isinstance(sp, dict):
            st = {} if not isinstance(st, dict) else st
            sp = {} if not isinstance(sp, dict) else sp
        n_used = int(it.get("records_used", 0) or 0)
        start_rate = float(st.get("rate", float("nan")))
        stop_rate = float(sp.get("rate", float("nan")))
        z_start = float(st.get("z", float("nan")))
        z_stop = float(sp.get("z", float("nan")))
        rows.append(
            f"{tex_path(it.get('label','-'))} & {it.get('code_id','-')} & {n_used} & "
            f"{start_rate:.4f} & {z_start:.2f} & {stop_rate:.4f} & {z_stop:.2f} \\\\"
        )
    write_text(generated_dir() / "nonstandard_sequence_tests_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

    summary_lines = []
    summary_lines.append(
        "Sequence-level nonstandard-code tests: start boundary-hit enrichment is evaluated against within-CDS background "
        "via a Poisson-binomial normal approximation; terminal-stop boundary-hit preference is evaluated against a null "
        "that selects uniformly from the translation table's stop set."
    )
    write_text(generated_dir() / "nonstandard_sequence_tests_summary.tex", "\n".join(summary_lines) + "\n")


def main() -> None:
    args = parse_args()
    out_json = Path(args.out_json)
    hb_global = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] nonstandard_sequence_tests")
    m = read_manifest()
    panels = m.get("panels") or {}
    if not isinstance(panels, dict):
        panels = {}
    pdef = panels.get(str(args.panel))

    # Fallback: some data bundles may ship without manifest.panels. If a cached output JSON exists,
    # reuse it and only re-emit LaTeX fragments.
    if not isinstance(pdef, dict):
        if out_json.exists():
            cached = _read_json_dict(out_json)
            if cached is None:
                raise SystemExit(f"Missing panel: {args.panel} (and cached summary is malformed: {out_json})")
            if not args.no_latex:
                _emit_latex_from_summary(cached)
                print("Wrote LaTeX fragments into:", generated_dir())
            print(f"[reuse] nonstandard_sequence_tests: manifest.panels missing '{args.panel}', using cached summary: {out_json}", flush=True)
            return
        raise SystemExit(f"Missing panel: {args.panel}")
    items = pdef.get("items") or []
    if not isinstance(items, list) or not items:
        raise SystemExit(f"Panel has no items: {args.panel}")

    gc_path = data_root() / "gc.prt"
    if not gc_path.exists():
        raise SystemExit("Missing data/gc.prt. Run scripts/fetch_datasets.py --dataset gc_prt first.")
    tables = parse_gc_prt(gc_path.read_text(encoding="utf-8", errors="replace"))
    by_id = {t.code_id: t for t in tables}

    # ---- Cache short-circuit ----
    datasets = m.get("datasets") if isinstance(m.get("datasets"), dict) else {}
    gc_sha: str | None = None
    if isinstance(datasets, dict):
        ds_gc = datasets.get("ncbi_gc_prt")
        if isinstance(ds_gc, dict):
            sha = ds_gc.get("sha256")
            if isinstance(sha, str) and sha:
                gc_sha = sha
    if gc_sha is None:
        st = gc_path.stat()
        gc_sha = f"stat:{st.st_size}:{getattr(st, 'st_mtime_ns', int(st.st_mtime * 1e9))}"

    item_fps: list[dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        dataset_key = str(it.get("dataset") or "")
        if not dataset_key:
            continue
        files = dataset_files_from_manifest(m, dataset_key)
        present = [fp for fp in files if fp.exists()]
        ds = datasets.get(dataset_key) if isinstance(datasets, dict) else None
        file_meta_by_name: dict[str, dict[str, object]] = {}
        if isinstance(ds, dict):
            if isinstance(ds.get("files"), list):
                for e in (ds.get("files") or []):
                    if not isinstance(e, dict):
                        continue
                    nm = e.get("name")
                    if isinstance(nm, str) and nm:
                        file_meta_by_name[nm] = dict(e)
            lp = ds.get("local_path")
            if isinstance(lp, str) and lp:
                file_meta_by_name[Path(lp).name] = {"name": Path(lp).name, "sha256": ds.get("sha256"), "bytes": ds.get("bytes")}
        fp_list: list[dict[str, object]] = []
        for fp in present:
            e = file_meta_by_name.get(fp.name) or {}
            sha = e.get("sha256")
            if isinstance(sha, str) and sha:
                fp_list.append({"name": fp.name, "sha256": sha, "bytes": int(e.get("bytes", fp.stat().st_size) or fp.stat().st_size)})
            else:
                st2 = fp.stat()
                fp_list.append({"name": fp.name, "bytes": int(st2.st_size), "mtime_ns": int(getattr(st2, "st_mtime_ns", int(st2.st_mtime * 1e9)))})
        fp_list.sort(key=lambda x: str(x.get("name") or ""))
        item_fps.append(
            {
                "dataset": dataset_key,
                "code_id": int(it.get("code_id") or 1),
                "present_n": int(len(present)),
                "files": fp_list,
            }
        )
    item_fps.sort(key=lambda x: str(x.get("dataset") or ""))

    # Map for per-item caches: key=(dataset, code_id) -> fingerprint entry.
    item_fp_map: dict[tuple[str, int], dict[str, object]] = {}
    for e in item_fps:
        try:
            ds = str(e.get("dataset") or "")
            cid = int(e.get("code_id") or 1)
        except Exception:
            continue
        if ds:
            item_fp_map[(ds, int(cid))] = e

    cache_key = {
        "analysis": "nonstandard_sequence_tests",
        "analysis_version": int(ANALYSIS_VERSION),
        "panel": str(args.panel),
        "max_records": int(args.max_records),
        "mu_star": MU_STAR,
        "gc_prt": gc_sha,
        "items": item_fps,
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_json, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_json}")
        if args.no_latex:
            return
        try:
            cached = json.loads(out_json.read_text(encoding="utf-8"))
        except Exception:
            cached = None
        if not isinstance(cached, dict):
            raise SystemExit("Cached nonstandard_sequence_tests.json is malformed; rerun with --force.")
        _emit_latex_from_summary(cached)
        print("Wrote LaTeX fragments into:", generated_dir())
        return

    # ---- Per-item caches (avoid rescanning unaffected datasets) ----
    item_cache_dir = nonstandard_item_cache_dir()

    # Best-effort: seed per-item caches from an existing panel summary JSON (even if panel cache miss),
    # so formatting-only changes do not force rescans.
    if (not args.force) and out_json.exists():
        old = _read_json_dict(out_json)
        if (
            isinstance(old, dict)
            and int(old.get("analysis_version", 0) or 0) == int(ANALYSIS_VERSION)
            and str(old.get("panel") or "") == str(args.panel)
        ):
            old_items = old.get("items") or []
            if isinstance(old_items, list):
                for oit in old_items:
                    if not isinstance(oit, dict) or not oit.get("present"):
                        continue
                    ds0 = str(oit.get("dataset") or "")
                    cid0 = int(oit.get("code_id") or 1)
                    fp0 = item_fp_map.get((ds0, int(cid0))) or {}
                    item_cache_key0 = {
                        "analysis": "nonstandard_sequence_tests_item",
                        "analysis_version": int(ANALYSIS_VERSION),
                        "panel": str(args.panel),
                        "dataset": ds0,
                        "code_id": int(cid0),
                        "max_records": int(args.max_records),
                        "mu_star": MU_STAR,
                        "gc_prt": gc_sha,
                        "fingerprint": fp0,
                    }
                    meta0 = {"cache_key": item_cache_key0, "cache_digest": cache_key_digest(item_cache_key0)}
                    item_json0 = item_cache_dir / f"{meta0['cache_digest']}.json"
                    if item_json0.exists() and cache_meta_path(item_json0).exists():
                        continue
                    write_json_atomic(item_json0, oit)
                    write_json_atomic(cache_meta_path(item_json0), meta0)

    out_items: list[dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        dataset_key = str(it.get("dataset") or "")
        if not dataset_key:
            continue
        code_id = int(it.get("code_id") or 1)
        label = str(it.get("label") or dataset_key)
        domain = str(it.get("domain") or "")

        if code_id not in by_id:
            raise SystemExit(f"Translation table code_id={code_id} not found in gc.prt")
        t = by_id[code_id]
        codons = codons_for_table(t)
        stop_codons = sorted({codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*"})
        start_codons = sorted({codons[i] for i, aa in enumerate(t.sncbieaa) if aa.upper() == "M"})

        stop_boundary = [c for c in stop_codons if fold_is_boundary(c)]
        start_boundary = [c for c in start_codons if fold_is_boundary(c)]
        p_stop_boundary = (len(stop_boundary) / float(len(stop_codons))) if stop_codons else float("nan")

        files = dataset_files_from_manifest(m, dataset_key)
        present = [fp for fp in files if fp.exists()]
        if not present:
            out_items.append(
                {
                    "dataset": dataset_key,
                    "label": label,
                    "domain": domain,
                    "code_id": code_id,
                    "present": False,
                    "files": [str(fp) for fp in files],
                    "error": "missing_files",
                }
            )
            continue

        # Per-item cache.
        fp_entry = item_fp_map.get((dataset_key, int(code_id))) or {
            "dataset": dataset_key,
            "code_id": int(code_id),
            "present_n": int(len(present)),
            "files": [{"name": fp.name} for fp in present],
        }
        item_cache_key = {
            "analysis": "nonstandard_sequence_tests_item",
            "analysis_version": int(ANALYSIS_VERSION),
            "panel": str(args.panel),
            "dataset": dataset_key,
            "code_id": int(code_id),
            "max_records": int(args.max_records),
            "mu_star": MU_STAR,
            "gc_prt": gc_sha,
            "fingerprint": fp_entry,
        }
        item_meta = {"cache_key": item_cache_key, "cache_digest": cache_key_digest(item_cache_key)}
        item_json = item_cache_dir / f"{item_meta['cache_digest']}.json"
        if (not args.force) and cache_hit(item_json, expected_meta=item_meta, require_meta=True):
            cached_item = _read_json_dict(item_json)
            if isinstance(cached_item, dict) and cached_item.get("present"):
                # Keep metadata aligned with manifest.
                cached_item["label"] = label
                cached_item["domain"] = domain
                cached_item["files"] = [str(fp) for fp in present]
                out_items.append(cached_item)  # type: ignore[arg-type]
                continue

        hb = Heartbeat(every_s=float(args.heartbeat_s), prefix=f"[progress] nonstandard_sequence_tests:{dataset_key}")
        hb.force(f"start code_id={code_id} files={len(present)}")

        n_seen = 0
        n_used = 0
        n_invalid = 0
        start_not_in_set = 0
        stop_not_in_set = 0

        start_counts: Counter[str] = Counter()
        stop_counts: Counter[str] = Counter()
        start_boundary_hits = 0
        stop_boundary_hits = 0

        # Within-CDS background for start test: Poisson-binomial approximation.
        # For each CDS i, p_i = boundary_rate over internal codons (excluding start and terminal stop).
        p_internal: list[float] = []

        for fp in present:
            hb_global.maybe(f"active_dataset={dataset_key} active_file={fp.name}")
            for _rid, seq in iter_fasta(str(fp)):
                n_seen += 1
                if args.max_records and n_seen > int(args.max_records):
                    break

                L = (len(seq) // 3) * 3
                if L < 9:
                    n_invalid += 1
                    continue
                codon_list = [seq[i : i + 3] for i in range(0, L, 3)]
                if any(c not in GENETIC_CODE for c in codon_list):
                    n_invalid += 1
                    continue

                start_c = codon_list[0]
                stop_c = codon_list[-1]
                if stop_c not in stop_codons:
                    stop_not_in_set += 1
                    continue
                if start_c not in start_codons:
                    start_not_in_set += 1
                    # Still include, but record separately.

                n_used += 1
                start_counts[start_c] += 1
                stop_counts[stop_c] += 1

                if fold_is_boundary(start_c):
                    start_boundary_hits += 1
                if fold_is_boundary(stop_c):
                    stop_boundary_hits += 1

                internal = codon_list[1:-1]
                if internal:
                    b = 0
                    for c in internal:
                        if fold_is_boundary(c):
                            b += 1
                    p_internal.append(b / float(len(internal)))

                # Heartbeat (time-based) so terminals never go silent during long scans.
                hb.maybe(
                    f"file={fp.name} seen={n_seen} used={n_used} invalid={n_invalid} "
                    f"start_not_in_set={start_not_in_set} stop_not_in_set={stop_not_in_set}"
                )

            if args.max_records and n_seen > int(args.max_records):
                break

        # Start test: observed hits vs within-CDS background (Poisson-binomial normal approximation).
        mu = float(sum(p_internal))
        var = float(sum(p * (1.0 - p) for p in p_internal))
        z_start = (float(start_boundary_hits) - mu) / math.sqrt(var) if var > 0 else 0.0
        p_start = normal_two_sided_p(z_start) if var > 0 else 1.0

        # Stop test: observed boundary hits vs uniform over stop set.
        mu_s = float(n_used) * float(p_stop_boundary) if (n_used > 0 and not math.isnan(p_stop_boundary)) else 0.0
        var_s = float(n_used) * float(p_stop_boundary) * (1.0 - float(p_stop_boundary)) if (n_used > 0 and 0.0 < p_stop_boundary < 1.0) else 0.0
        z_stop = (float(stop_boundary_hits) - mu_s) / math.sqrt(var_s) if var_s > 0 else 0.0
        p_stop = normal_two_sided_p(z_stop) if var_s > 0 else 1.0

        hb.force(f"done seen={n_seen} used={n_used} invalid={n_invalid}")
        out_items.append(
            {
                "dataset": dataset_key,
                "label": label,
                "domain": domain,
                "code_id": code_id,
                "present": True,
                "files": [str(fp) for fp in present],
                "records_seen": int(n_seen),
                "records_used": int(n_used),
                "records_invalid": int(n_invalid),
                "start_not_in_start_set": int(start_not_in_set),
                "stop_not_in_stop_set": int(stop_not_in_set),
                "start_codons": start_codons,
                "stop_codons": stop_codons,
                "start_boundary_codons": start_boundary,
                "stop_boundary_codons": stop_boundary,
                "start_counts": {k: int(v) for k, v in sorted(start_counts.items())},
                "stop_counts": {k: int(v) for k, v in sorted(stop_counts.items())},
                "tests": {
                    "start_boundary": {
                        "hits": int(start_boundary_hits),
                        "n": int(n_used),
                        "rate": (start_boundary_hits / float(n_used) if n_used else float("nan")),
                        "null_mean": mu,
                        "null_var": var,
                        "z": z_start,
                        "p_two_sided": p_start,
                    },
                    "stop_boundary": {
                        "hits": int(stop_boundary_hits),
                        "n": int(n_used),
                        "rate": (stop_boundary_hits / float(n_used) if n_used else float("nan")),
                        "p0_uniform_over_stop_set": p_stop_boundary,
                        "z": z_stop,
                        "p_two_sided": p_stop,
                    },
                },
            }
        )
        # Persist per-item cache (post-scan).
        try:
            write_json_atomic(item_json, out_items[-1])
            write_json_atomic(cache_meta_path(item_json), item_meta)
        except Exception:
            pass

    out = {"schema_version": 1, "panel": str(args.panel), "mu_star": MU_STAR, "items": out_items}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out["analysis_version"] = int(ANALYSIS_VERSION)
    write_json_atomic(out_json, out)
    write_json_atomic(cache_meta_path(out_json), cache_meta)
    print("Wrote:", out_json)

    if args.no_latex:
        return

    _emit_latex_from_summary(out)
    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


