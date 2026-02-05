# -*- coding: utf-8 -*-
"""
Run the full reproducible pipeline for this paper.

This orchestrator:
  - executes all generator scripts in a deterministic order,
  - caches step fingerprints based on content-hash of local dependencies,
  - checks that expected LaTeX fragments were produced and are non-empty.

Caching is enabled by default. Disable with:
  export HPA_NO_CACHE=1
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from common_cache import cache_disabled, cache_path, load_pickle, save_pickle_atomic
from common_paths import generated_dir, paper_root, scripts_dir
from common_tex import nonempty_file


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    expected_outputs: Sequence[str]
    always_run: bool = False


RUN_ALL_CACHE_VERSION = 1


def _run_all_cache_file() -> Path:
    return cache_path("run_all_steps.pkl")


def _load_run_all_cache() -> Dict[str, str]:
    """
    Mapping: step.script -> dependency fingerprint (sha256 hex).
    """
    p = _run_all_cache_file()
    if cache_disabled() or (not p.is_file()):
        return {}
    try:
        obj = load_pickle(p)
        if not isinstance(obj, dict):
            return {}
        if int(obj.get("version", -1)) != RUN_ALL_CACHE_VERSION:
            return {}
        steps = obj.get("steps", {})
        if not isinstance(steps, dict):
            return {}
        out: Dict[str, str] = {}
        for k, v in steps.items():
            if isinstance(k, str) and isinstance(v, str):
                out[k] = v
        return out
    except Exception:
        return {}


def _save_run_all_cache(cache: Dict[str, str]) -> None:
    if cache_disabled():
        return
    try:
        save_pickle_atomic(_run_all_cache_file(), {"version": RUN_ALL_CACHE_VERSION, "steps": dict(cache)})
    except Exception:
        # Best-effort; never fail the pipeline because of caching.
        pass


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _deps_fingerprint(script_path: Path, extra_deps: Iterable[Path] = ()) -> str:
    """
    Stable fingerprint for a step. Keep it explicit and auditable:
      - step script content hash
      - shared helpers used by our pipeline
    We intentionally exclude this orchestrator itself to avoid forcing a recompute
    when editing run_all.py.
    """
    deps = [
        script_path,
        scripts_dir() / "common_cache.py",
        scripts_dir() / "common_paths.py",
        scripts_dir() / "common_tex.py",
    ]
    deps.extend(list(extra_deps))
    deps = [p for p in deps if p.is_file()]

    h = hashlib.sha256()
    for p in sorted(set(deps), key=lambda x: str(x.resolve())):
        rel = str(p.resolve())
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(_file_sha256(p).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def _run_script(script_path: Path, step_name: str) -> None:
    cmd = [sys.executable, str(script_path)]
    proc = subprocess.run(cmd, cwd=str(paper_root()))
    if proc.returncode != 0:
        raise RuntimeError(f"Step failed: {step_name} ({script_path.name}), rc={proc.returncode}")


def _check_outputs(rel_paths: Iterable[str]) -> None:
    missing: List[str] = []
    for rel in rel_paths:
        p = paper_root() / rel
        if not nonempty_file(p):
            missing.append(rel)
    if missing:
        msg = "Missing/empty generated outputs:\n" + "\n".join(f"  - {m}" for m in missing)
        raise RuntimeError(msg)


def build_steps() -> List[Step]:
    # Keep this list explicit and small.
    return [
        Step(
            name="WL experiments (trellis and Q_n)",
            script="wl_experiments.py",
            expected_outputs=[
                "sections/generated/wl_experiments_manifest.json",
                "sections/generated/wl_summary.json",
                "sections/generated/trellis_wl1.csv",
                "sections/generated/trellis_wl2.csv",
                "sections/generated/Qn_wl2_weighted.csv",
                "sections/generated/wl_table_summary.tex",
            ],
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all reproducible generators for this paper.")
    parser.add_argument("--force", action="store_true", help="Force recompute of all steps.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    steps = build_steps()
    cache: Dict[str, str] = _load_run_all_cache() if (not args.force) else {}
    cache_dirty = False

    for step in steps:
        script_path = scripts_dir() / step.script
        if not script_path.is_file():
            raise FileNotFoundError(f"Missing script: {script_path}")

        fp = _deps_fingerprint(script_path)
        cached_fp = cache.get(step.script)

        have = True
        for rel in step.expected_outputs:
            if not nonempty_file(paper_root() / rel):
                have = False
                break

        should_run = args.force or step.always_run or (not have) or (cached_fp != fp)

        if should_run:
            print(f"[run_all] {step.name} -> {step.script}", flush=True)
            _run_script(script_path, step_name=step.name)
            _check_outputs(step.expected_outputs)
            if not cache_disabled():
                cache[step.script] = fp
                cache_dirty = True
        else:
            print(f"[run_all] SKIP (up-to-date) {step.name}", flush=True)
            _check_outputs(step.expected_outputs)

    if cache_dirty:
        _save_run_all_cache(cache)

    print("[run_all] OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

