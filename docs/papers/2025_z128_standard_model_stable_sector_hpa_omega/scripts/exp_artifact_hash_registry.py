# -*- coding: utf-8 -*-
"""
Artifact hash registry (audit + caching convenience).

This script builds a dictionary that maps:
  - script/dependency content hashes -> generated artifact content hashes

It is designed as a lightweight, deterministic cache index that can be used
externally (or by future cache layers) without relying on mtimes.

Outputs:
  - sections/generated/artifact_hash_registry.json
  - sections/generated/artifact_hash_registry_summary.tex
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from common_paths import paper_root, scripts_dir, generated_dir
from common_tex import write_lines

import run_all  # uses build_steps and dependency-closure helpers


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    return _sha256_bytes(p.read_bytes())


def _rel_to_paper(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(paper_root().resolve()))
    except Exception:
        return str(p)


def main() -> None:
    steps = run_all.build_steps()
    module_map = run_all._local_module_map()
    deps_memo: dict[Path, set[Path]] = {}

    records: List[Dict[str, Any]] = []
    for st in steps:
        script_path = scripts_dir() / st.script
        deps = run_all._script_deps_closure(script_path, module_map, deps_memo)
        extra_inputs = [paper_root() / p for p in getattr(st, "depends_on", [])]
        dep_fp = run_all._deps_fingerprint(set(deps) | set(extra_inputs))
        script_hash = _sha256_file(script_path) if script_path.is_file() else ""

        outputs: List[Dict[str, Any]] = []
        out_hash_acc = hashlib.sha256()
        for rel in st.expected_outputs:
            p = paper_root() / rel
            if p.is_file():
                h = _sha256_file(p)
                sz = p.stat().st_size
            else:
                h = ""
                sz = 0
            outputs.append({"path": rel, "sha256": h, "bytes": int(sz)})
            out_hash_acc.update(rel.encode("utf-8"))
            out_hash_acc.update(b"\0")
            out_hash_acc.update(h.encode("utf-8"))
            out_hash_acc.update(b"\0")

        rec: Dict[str, Any] = {
            "name": st.name,
            "script": st.script,
            "script_sha256": script_hash,
            "deps_fingerprint_sha256": dep_fp,
            "depends_on": list(getattr(st, "depends_on", [])),
            "expected_outputs": list(st.expected_outputs),
            "outputs": outputs,
            "outputs_fingerprint_sha256": out_hash_acc.hexdigest(),
        }
        records.append(rec)

    payload = {
        "version": 1,
        "paper_root": str(paper_root()),
        "scripts_dir": str(scripts_dir()),
        "records": records,
    }

    out_json = generated_dir() / "artifact_hash_registry.json"
    new_json = json.dumps(payload, indent=2, sort_keys=True)
    old_json = out_json.read_text(encoding="utf-8") if out_json.is_file() else ""
    if new_json != old_json:
        out_json.write_text(new_json, encoding="utf-8")

    # Minimal LaTeX summary.
    summary = [
        r"\paragraph{Audit summary (artifact hash registry).} \AuditTag "
        r"We write a JSON dictionary that records, for each generator step, the script hash, "
        r"the transitive local dependency fingerprint, and the content hashes of expected outputs. "
        r"This provides a content-addressable cache index independent of mtimes. "
        rf"File: \texttt{{{_rel_to_paper(out_json)}}}.",
    ]
    out_tex = generated_dir() / "artifact_hash_registry_summary.tex"
    new_tex = "\n".join(summary) + "\n"
    old_tex = out_tex.read_text(encoding="utf-8") if out_tex.is_file() else ""
    if new_tex != old_tex:
        write_lines(out_tex, summary)


if __name__ == "__main__":
    main()

