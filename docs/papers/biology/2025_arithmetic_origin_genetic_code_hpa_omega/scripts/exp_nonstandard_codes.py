# -*- coding: utf-8 -*-
"""
Nonstandard genetic code scan (NCBI translation tables).

Parse NCBI gc.prt (data/gc.prt), extract stop/start codon sets for each
translation table, and compute Fold_6 boundary-hit metrics under mu*.

Outputs LaTeX fragments under sections/generated/.

Standard library only.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import BOUNDARY_WORDS, fold_codon


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 2


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def data_path() -> Path:
    return root_dir() / "data" / "gc.prt"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _read_json_dict(path: Path) -> dict[str, object] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


@dataclass(frozen=True)
class CodeTable:
    code_id: int
    names: list[str]
    ncbieaa: str
    sncbieaa: str
    base1: str
    base2: str
    base3: str

    def primary_name(self) -> str:
        return self.names[0] if self.names else f"code_{self.code_id}"


_QUOTED_RE = re.compile(r"\"([^\"]*)\"")


def _parse_quoted(s: str) -> str | None:
    m = _QUOTED_RE.search(s)
    if not m:
        return None
    return m.group(1)


def parse_gc_prt(text: str) -> list[CodeTable]:
    """
    Minimal parser for NCBI gc.prt format.
    """
    lines = text.splitlines()
    tables: list[CodeTable] = []
    depth = 0
    cur: dict[str, object] | None = None

    for raw in lines:
        s = raw.strip()
        if not s:
            continue

        if s.startswith("Genetic-code-table") and s.endswith("{"):
            # Outer container opens on the same line.
            depth = 1
            continue
        if s.startswith("Genetic-code-table"):
            continue

        if s == "{":
            depth += 1
            if depth == 2:
                cur = {"names": []}
            continue

        if s.startswith("}"):
            s0 = s.replace(" ", "")
            if s0 not in ("}", "},"):
                continue
            if depth == 2 and cur is not None:
                try:
                    tables.append(
                        CodeTable(
                            code_id=int(cur["id"]),  # type: ignore[arg-type]
                            names=list(cur.get("names", [])),  # type: ignore[list-item]
                            ncbieaa=str(cur["ncbieaa"]),
                            sncbieaa=str(cur["sncbieaa"]),
                            base1=str(cur["base1"]),
                            base2=str(cur["base2"]),
                            base3=str(cur["base3"]),
                        )
                    )
                except Exception:
                    pass
                cur = None
            depth -= 1
            continue

        if cur is None or depth != 2:
            continue

        if s.startswith("name"):
            q = _parse_quoted(s)
            if q is not None:
                cur["names"] = list(cur.get("names", [])) + [q]
            continue

        if s.startswith("id "):
            parts = s.replace(",", "").split()
            if len(parts) >= 2:
                cur["id"] = int(parts[1])
            continue

        if s.startswith("ncbieaa"):
            q = _parse_quoted(s)
            if q is not None:
                cur["ncbieaa"] = q
            continue

        if s.startswith("sncbieaa"):
            q = _parse_quoted(s)
            if q is not None:
                cur["sncbieaa"] = q
            continue

        # Base strings are stored as comment lines.
        if s.startswith("-- Base1"):
            cur["base1"] = s.split(None, 2)[2].strip()
            continue
        if s.startswith("-- Base2"):
            cur["base2"] = s.split(None, 2)[2].strip()
            continue
        if s.startswith("-- Base3"):
            cur["base3"] = s.split(None, 2)[2].strip()
            continue

    # Filter to well-formed tables.
    out: list[CodeTable] = []
    for t in tables:
        if len(t.ncbieaa) == 64 and len(t.sncbieaa) == 64 and len(t.base1) == 64 and len(t.base2) == 64 and len(t.base3) == 64:
            out.append(t)
    out.sort(key=lambda x: x.code_id)
    return out


def codons_for_table(t: CodeTable) -> list[str]:
    """
    Return RNA codons in the gc.prt order.
    """
    out = []
    for i in range(64):
        dna = (t.base1[i] + t.base2[i] + t.base3[i]).upper()
        out.append(dna.replace("T", "U"))
    return out


def _base_perm_to_str(base_map: dict[str, str]) -> str:
    """
    Compact representation of a base permutation: images of A,C,G,U in that order.
    Example: identity -> 'ACGU'.
    """
    return "".join(base_map[b] for b in "ACGU")


def _apply_action(codon: str, *, pos: tuple[int, int, int], base_map: dict[str, str]) -> str:
    return "".join(base_map[codon[i]] for i in pos)


def _best_symmetry_action(
    baseline_set: set[str],
    target_set: set[str],
    *,
    actions: list[tuple[tuple[int, int, int], dict[str, str]]],
) -> dict[str, object]:
    """
    Return the action (pos permutation + base permutation) that maximizes overlap between
    image(baseline_set) and target_set. Report overlap and Jaccard similarity.
    """
    best: dict[str, object] | None = None
    best_key: tuple[int, float, str, str] | None = None

    for pos, base_map in actions:
        img = {_apply_action(c, pos=pos, base_map=base_map) for c in baseline_set}
        inter = len(img & target_set)
        union = len(img | target_set)
        j = (float(inter) / float(union)) if union > 0 else 1.0
        pos_s = "".join(str(int(i) + 1) for i in pos)
        base_s = _base_perm_to_str(base_map)
        key = (int(inter), float(j), pos_s, base_s)
        if best_key is None or key > best_key:
            best_key = key
            best = {
                "pos": pos_s,
                "base": base_s,
                "overlap": int(inter),
                "jaccard": float(j),
            }

    return best or {"pos": "123", "base": "ACGU", "overlap": 0, "jaccard": 0.0}


def main() -> None:
    p = argparse.ArgumentParser(description="Nonstandard code scan (NCBI gc.prt)")
    p.add_argument("--out-rows", default=str(generated_dir() / "nonstandard_code_rows.tex"))
    p.add_argument("--out-summary", default=str(generated_dir() / "nonstandard_code_summary.tex"))
    p.add_argument("--out-stop-migration-rows", default=str(generated_dir() / "nonstandard_stop_migration_rows.tex"))
    p.add_argument("--out-stop-migration-summary", default=str(generated_dir() / "nonstandard_stop_migration_summary.tex"))
    p.add_argument("--out-json", default=str(data_root() / "nonstandard_codes_summary.json"))
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    args = p.parse_args()

    # ---- Cache short-circuit ----
    gc = data_path()
    if not gc.exists():
        raise SystemExit("Missing data/gc.prt. Run scripts/fetch_datasets.py --dataset gc_prt first.")

    gc_sha: str | None = None
    mp = data_root() / "manifest.json"
    if mp.exists():
        m = _read_json_dict(mp)
        if isinstance(m, dict):
            ds = (m.get("datasets") or {}).get("ncbi_gc_prt") if isinstance(m.get("datasets"), dict) else None
            if isinstance(ds, dict):
                sha = ds.get("sha256")
                if isinstance(sha, str) and sha:
                    gc_sha = sha
    if gc_sha is None:
        st = gc.stat()
        gc_sha = f"stat:{st.st_size}:{getattr(st, 'st_mtime_ns', int(st.st_mtime * 1e9))}"

    out_rows = Path(args.out_rows)
    out_summary = Path(args.out_summary)
    out_stop_mig_rows = Path(args.out_stop_migration_rows)
    out_stop_mig_summary = Path(args.out_stop_migration_summary)
    out_json = Path(args.out_json)
    cache_file = data_root() / "_cache" / f"nonstandard_codes_v{int(ANALYSIS_VERSION)}.json"
    cache_key = {
        "analysis": "nonstandard_codes",
        "analysis_version": int(ANALYSIS_VERSION),
        "mu_star": MU_STAR,
        "gc_prt": gc_sha,
        "out_rows": str(out_rows),
        "out_summary": str(out_summary),
        "out_stop_migration_rows": str(out_stop_mig_rows),
        "out_stop_migration_summary": str(out_stop_mig_summary),
        "out_json": str(out_json),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (
        (not args.force)
        and out_rows.exists()
        and out_summary.exists()
        and out_stop_mig_rows.exists()
        and out_stop_mig_summary.exists()
        and out_json.exists()
        and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True)
    ):
        print(f"[cache] hit: {cache_file}")
        print("Wrote LaTeX fragments into:", generated_dir())
        return

    text = gc.read_text(encoding="utf-8", errors="replace")
    tables = parse_gc_prt(text)
    if not tables:
        raise SystemExit("Failed to parse any translation tables from data/gc.prt")

    rows = []
    max_stop_boundary = -1
    max_ids: list[int] = []
    json_items: list[dict[str, object]] = []

    # Baseline (standard genetic code) for migration and symmetry comparisons.
    baseline = next((t for t in tables if int(t.code_id) == 1), tables[0])
    baseline_codons = codons_for_table(baseline)
    baseline_stops = {baseline_codons[i] for i, aa in enumerate(baseline.ncbieaa) if aa == "*"}
    baseline_starts = {baseline_codons[i] for i, aa in enumerate(baseline.sncbieaa) if aa.upper() == "M"}

    # Action group: base permutations (4!) × codon-position permutations (3!).
    bases = "ACGU"
    actions: list[tuple[tuple[int, int, int], dict[str, str]]] = []
    for perm in itertools.permutations(bases):
        base_map = dict(zip(bases, perm))
        for pos in itertools.permutations((0, 1, 2)):
            actions.append((pos, base_map))

    stop_mig_rows: list[str] = []
    perfect_stop_sym: list[tuple[int, str, str]] = []

    for t in tables:
        codons = codons_for_table(t)
        stops = [codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*"]
        starts = [codons[i] for i, aa in enumerate(t.sncbieaa) if aa.upper() == "M"]
        stop_set = set(stops)
        start_set = set(starts)

        stop_boundary_details = []
        for c in stops:
            w = fold_codon(c, MU_STAR).w
            if w in BOUNDARY_WORDS:
                stop_boundary_details.append({"codon": c, "w": w})
        start_boundary_details = []
        for c in starts:
            w = fold_codon(c, MU_STAR).w
            if w in BOUNDARY_WORDS:
                start_boundary_details.append({"codon": c, "w": w})
        stop_boundary = [d["codon"] for d in stop_boundary_details]
        start_boundary = [d["codon"] for d in start_boundary_details]

        if len(stop_boundary) > max_stop_boundary:
            max_stop_boundary = len(stop_boundary)
            max_ids = [t.code_id]
        elif len(stop_boundary) == max_stop_boundary:
            max_ids.append(t.code_id)

        stop_str = ", ".join(stops) if stops else "-"
        start_str = ", ".join(starts) if starts else "-"
        stop_b_str = ", ".join(f"{d['codon']}({d['w']})" for d in stop_boundary_details) if stop_boundary_details else "-"
        start_b_str = ", ".join(f"{d['codon']}({d['w']})" for d in start_boundary_details) if start_boundary_details else "-"

        # Keep name short to avoid overfull boxes in tables.
        name = t.primary_name()
        if len(name) > 44:
            name = name[:41] + "..."

        rows.append(
            f"{t.code_id} & {name} & {len(stops)} & {stop_str} & {len(stop_boundary)} & {stop_b_str} & "
            f"{len(starts)} & {start_str} & {len(start_boundary)} & {start_b_str} \\\\"
        )

        # Stop-set migration vs baseline code.
        added = sorted(stop_set - baseline_stops)
        removed = sorted(baseline_stops - stop_set)
        added_s = ", ".join(added) if added else "-"
        removed_s = ", ".join(removed) if removed else "-"

        # Best symmetry action (approximate): maximize overlap between image(baseline stops) and current stops.
        best_stop = _best_symmetry_action(baseline_stops, stop_set, actions=actions)
        pos_s = str(best_stop.get("pos") or "123")
        base_s = str(best_stop.get("base") or "ACGU")
        ov = int(best_stop.get("overlap") or 0)
        jac = float(best_stop.get("jaccard") or 0.0)
        sym_s = f"\\texttt{{pos{pos_s}/map{base_s}}}"
        if jac == 1.0 and ov == len(stop_set):
            perfect_stop_sym.append((int(t.code_id), pos_s, base_s))

        # Boundary-stop word (if any) as the migration anchor in boundary space.
        stop_b_one = "-"
        if stop_boundary_details:
            d0 = stop_boundary_details[0]
            stop_b_one = f"{d0['codon']}(\\texttt{{{d0['w']}}})"

        stop_mig_rows.append(
            f"{t.code_id} & {len(stops)} & {stop_str} & {added_s} & {removed_s} & {stop_b_one} & {sym_s} & {ov} & {jac:.3f} \\\\"
        )

        json_items.append(
            {
                "code_id": int(t.code_id),
                "name": t.primary_name(),
                "stops": stops,
                "starts": starts,
                "stop_boundary": stop_boundary_details,
                "start_boundary": start_boundary_details,
                "baseline_code_id": int(baseline.code_id),
                "stops_added": added,
                "stops_removed": removed,
                "starts_added": sorted(start_set - baseline_starts),
                "starts_removed": sorted(baseline_starts - start_set),
                "best_sym_stop": best_stop,
                "best_sym_start": _best_symmetry_action(baseline_starts, start_set, actions=actions) if baseline_starts else None,
            }
        )

    write_text(Path(args.out_rows), "\n".join(rows) + "\n\\bottomrule\n")

    # Stop migration fragment.
    write_text(out_stop_mig_rows, "\n".join(stop_mig_rows) + "\n\\bottomrule\n")

    mig_summary: list[str] = []
    mig_summary.append(
        f"Stop-set migration and symmetry scores are reported relative to baseline code ID {int(baseline.code_id)} "
        f"(baseline stops: {', '.join(sorted(baseline_stops))}). "
        f"The symmetry score maximizes overlap between the image of the baseline stop set under base/position permutations and the target stop set."
    )
    if perfect_stop_sym:
        ids = ", ".join(str(x[0]) for x in sorted(perfect_stop_sym))
        mig_summary.append(f"Perfect stop-set symmetry (Jaccard=1) occurs for code IDs: {ids}.")
    write_text(out_stop_mig_summary, "\n".join(mig_summary) + "\n")

    summary = []
    summary.append(
        f"From NCBI \\path{{gc.prt}} we parsed {len(tables)} translation tables. "
        f"The maximum number of boundary-hit stop codons under $\\mu^\\ast$ is {max_stop_boundary}, "
        f"achieved by code IDs: {', '.join(str(x) for x in sorted(max_ids))}."
    )
    write_text(Path(args.out_summary), "\n".join(summary) + "\n")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        out_json,
        {
            "schema_version": 2,
            "analysis_version": int(ANALYSIS_VERSION),
            "mu_star": MU_STAR,
            "gc_prt": gc_sha,
            "n_tables": int(len(tables)),
            "max_stop_boundary": int(max_stop_boundary),
            "max_ids": [int(x) for x in sorted(max_ids)],
            "baseline_code_id": int(baseline.code_id),
            "baseline_stops": sorted(baseline_stops),
            "baseline_starts": sorted(baseline_starts),
            "items": json_items,
        },
    )

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(cache_file, {"ok": True})
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote LaTeX fragments into:", generated_dir())
    print("Wrote:", out_json)


if __name__ == "__main__":
    main()


