#!/usr/bin/env python3
"""Generate Fold6 rule artifacts and LaTeX fragments (cached, reproducible).

Artifacts:
  artifacts/fold6_rules/<run_id>/
    - stable_words_x6.csv
    - interface_rule_5x5.csv
    - pair_rule_21x21.csv
    - manifest.json

LaTeX fragments (PyLaTeX):
  sections/generated/fold6_interface_rule_5x5_table.tex
  sections/generated/fold6_preimage_counts_summary.tex
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment
from hpa_ca_export_rules import export_interface_5x5, export_pair_rule_21x21, export_stable_words, stable_words_x6
from pylatex import Command


def _read_csv_rows(path: Path) -> List[List[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        rows = list(r)
    return rows


def main() -> None:
    script_path = Path(__file__).resolve()
    params = {}  # pure finite object; script hash acts as version.

    required = ["stable_words_x6.csv", "interface_rule_5x5.csv", "pair_rule_21x21.csv"]
    run = prepare_run("fold6_rules", params=params, script_path=script_path, required_files=required, force=False)

    if not run.cached:
        words = stable_words_x6()
        export_stable_words(words, str(run.run_dir))
        export_interface_5x5(str(run.run_dir))
        export_pair_rule_21x21(words, str(run.run_dir))

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Always (re-)emit LaTeX fragments deterministically.
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    # 5x5 interface table: show mapping (a,b)->(micro, out, uplift)
    iface_rows = _read_csv_rows(run.run_dir / "interface_rule_5x5.csv")
    header = iface_rows[0]
    data = iface_rows[1:]

    # Keep a compact view: left_suffix3, right_prefix3, fold6_word, uplift_value
    col_spec = "cccc"
    tex_header = [r"\texttt{L}", r"\texttt{R}", r"\texttt{Fold}\(_6\)(\texttt{LR})", r"$\Delta$"]
    tex_rows = [[Command("texttt", d[0]), Command("texttt", d[1]), Command("texttt", d[3]), d[4]] for d in data]
    write_tabular_fragment(
        gen / "fold6_interface_rule_5x5_table.tex",
        column_spec=col_spec,
        header=tex_header,
        rows=tex_rows,
        booktabs=True,
    )

    # Minimal summary as a 2-row tabular to avoid hand-written TeX strings.
    write_tabular_fragment(
        gen / "fold6_preimage_counts_summary.tex",
        column_spec="ll",
        header=[r"\textbf{key}", r"\textbf{value}"],
        rows=[
            [r"run\_id", Command("texttt", run.run_id)],
            [r"artifacts", Command("texttt", f"artifacts/{run.experiment}/{run.run_id}/".replace("_", r"\_"))],
        ],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

