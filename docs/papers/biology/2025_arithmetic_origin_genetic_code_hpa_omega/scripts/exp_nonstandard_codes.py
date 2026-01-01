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
import json
import re
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import BOUNDARY_WORDS, fold_codon


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


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


def main() -> None:
    p = argparse.ArgumentParser(description="Nonstandard code scan (NCBI gc.prt)")
    p.add_argument("--out-rows", default=str(generated_dir() / "nonstandard_code_rows.tex"))
    p.add_argument("--out-summary", default=str(generated_dir() / "nonstandard_code_summary.tex"))
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
    cache_file = data_root() / "_cache" / f"nonstandard_codes_v{int(ANALYSIS_VERSION)}.json"
    cache_key = {
        "analysis": "nonstandard_codes",
        "analysis_version": int(ANALYSIS_VERSION),
        "mu_star": MU_STAR,
        "gc_prt": gc_sha,
        "out_rows": str(out_rows),
        "out_summary": str(out_summary),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (
        (not args.force)
        and out_rows.exists()
        and out_summary.exists()
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

    for t in tables:
        codons = codons_for_table(t)
        stops = [codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*"]
        starts = [codons[i] for i, aa in enumerate(t.sncbieaa) if aa.upper() == "M"]

        stop_boundary = [c for c in stops if fold_codon(c, MU_STAR).w in BOUNDARY_WORDS]
        start_boundary = [c for c in starts if fold_codon(c, MU_STAR).w in BOUNDARY_WORDS]

        if len(stop_boundary) > max_stop_boundary:
            max_stop_boundary = len(stop_boundary)
            max_ids = [t.code_id]
        elif len(stop_boundary) == max_stop_boundary:
            max_ids.append(t.code_id)

        stop_str = ", ".join(stops) if stops else "-"
        start_str = ", ".join(starts) if starts else "-"
        stop_b_str = ", ".join(stop_boundary) if stop_boundary else "-"
        start_b_str = ", ".join(start_boundary) if start_boundary else "-"

        # Keep name short to avoid overfull boxes in tables.
        name = t.primary_name()
        if len(name) > 44:
            name = name[:41] + "..."

        rows.append(
            f"{t.code_id} & {name} & {len(stops)} & {stop_str} & {len(stop_boundary)} & {stop_b_str} & "
            f"{len(starts)} & {start_str} & {len(start_boundary)} & {start_b_str} \\\\"
        )

    write_text(Path(args.out_rows), "\n".join(rows) + "\n\\bottomrule\n")

    summary = []
    summary.append(
        f"From NCBI \\path{{gc.prt}} we parsed {len(tables)} translation tables. "
        f"The maximum number of boundary-hit stop codons under $\\mu^\\ast$ is {max_stop_boundary}, "
        f"achieved by code IDs: {', '.join(str(x) for x in sorted(max_ids))}."
    )
    write_text(Path(args.out_summary), "\n".join(summary) + "\n")

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(cache_file, {"ok": True})
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


