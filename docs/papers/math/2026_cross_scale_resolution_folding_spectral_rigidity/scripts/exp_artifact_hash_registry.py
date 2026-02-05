#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Artifact hash registry (paper-local).

Scans artifacts/<experiment>/<run_id>/manifest.json and produces:
  - sections/generated/artifact_hash_registry.json
  - sections/generated/artifact_hash_registry_summary.tex
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from common_hash import sha256_file
from common_paths import artifacts_dir, generated_dir, paper_root
from common_tex_pylatex import write_tabular_fragment
from pylatex import Command


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(paper_root().resolve()))
    except Exception:
        return str(p)


def main() -> None:
    art = artifacts_dir()
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    if art.is_dir():
        for exp_dir in sorted([p for p in art.iterdir() if p.is_dir()], key=lambda x: x.name):
            for run_dir in sorted([p for p in exp_dir.iterdir() if p.is_dir()], key=lambda x: x.name):
                man = run_dir / "manifest.json"
                if not man.is_file():
                    continue
                try:
                    payload = json.loads(man.read_text(encoding="utf-8"))
                except Exception:
                    continue
                records.append(
                    {
                        "experiment": exp_dir.name,
                        "run_id": run_dir.name,
                        "manifest_path": _rel(man),
                        "manifest_sha256": sha256_file(man),
                        "script": payload.get("script", ""),
                        "script_sha256": payload.get("script_sha256", ""),
                        "outputs": payload.get("outputs", []),
                    }
                )

    out_json = gen / "artifact_hash_registry.json"
    out_json.write_text(
        json.dumps({"version": 1, "records": records}, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    out_tex = gen / "artifact_hash_registry_summary.tex"
    write_tabular_fragment(
        out_tex,
        column_spec="lll",
        header=[r"\textbf{experiment}", r"\textbf{run\_id}", r"\textbf{manifest}"],
        rows=[
            [
                Command("texttt", r["experiment"].replace("_", r"\_")),
                Command("texttt", r["run_id"]),
                Command("texttt", r["manifest_sha256"][:12]),
            ]
            for r in records
        ],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

