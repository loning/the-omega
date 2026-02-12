#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the reproducible pipeline for this paper.

This paper is primarily theoretical; the default pipeline may be empty.
When experiments/tables are added, register them in `build_steps()`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from common_paths import export_dir, generated_dir, paper_root, scripts_dir


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    args: Sequence[str]
    expected_outputs: Sequence[str]


def _nonempty(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _cache_path() -> Path:
    return export_dir() / "run_all_cache.json"


def _load_cache() -> Dict[str, object]:
    p = _cache_path()
    if not p.is_file():
        return {"version": 1, "steps": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "steps": {}}


def _write_cache(cache: Dict[str, object]) -> None:
    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _step_signature(script_path: Path, args: Sequence[str]) -> Dict[str, object]:
    return {
        "script": script_path.name,
        "script_sha256": _sha256_file(script_path),
        "args": list(args),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def _outputs_ok(step: Step) -> Tuple[bool, List[str]]:
    missing: List[str] = []
    for rel in step.expected_outputs:
        p = paper_root() / rel
        if not _nonempty(p):
            missing.append(rel)
    return (len(missing) == 0), missing


def build_steps() -> List[Step]:
    # Register experiment/table generation steps here.
    return [
        Step(
            name="collision_moments",
            script="gen_collision_moments.py",
            args=["--m-min", "2", "--m-max", "18", "--k", "2", "--k", "3", "--table-m-max", "12"],
            expected_outputs=[
                "artifacts/export/collision_moments.csv",
                "sections/generated/tab_collision_rates.tex",
            ],
        ),
        Step(
            name="moment_kernel_spectra",
            script="gen_moment_kernel_spectra.py",
            args=["--k", "2", "--k", "3", "--input-alphabet", "01"],
            expected_outputs=[
                "artifacts/export/moment_kernel_spectra.csv",
                "sections/generated/tab_moment_kernel_spectra.tex",
            ],
        ),
    ]


def _run_step(step: Step) -> None:
    script_path = scripts_dir() / step.script
    if not script_path.is_file():
        raise FileNotFoundError(f"Missing script: {script_path}")
    cmd = [sys.executable, str(script_path), *step.args]
    t0 = time.time()
    print(f"[run_all] start step={step.name} cmd={' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd, cwd=str(paper_root()))
    dt = time.time() - t0
    ok, missing = _outputs_ok(step)
    if not ok:
        raise RuntimeError(f"Step '{step.name}' missing outputs: {missing}")
    print(f"[run_all] done step={step.name} elapsed_s={dt:.3f}", flush=True)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Run all reproducible pipeline steps.")
    parser.add_argument("--list", action="store_true", help="List steps and exit.")
    parser.add_argument("--force", action="store_true", help="Run steps even if cached outputs exist.")
    parser.add_argument("--only", action="append", default=[], help="Run only the named step(s).")
    args = parser.parse_args(list(argv))

    export_dir().mkdir(parents=True, exist_ok=True)
    generated_dir().mkdir(parents=True, exist_ok=True)

    steps = build_steps()
    if args.list:
        if not steps:
            print("[run_all] no steps registered", flush=True)
            return 0
        for s in steps:
            print(f"- {s.name}: {s.script} {list(s.args)}", flush=True)
        return 0

    if args.only:
        wanted = set(args.only)
        steps = [s for s in steps if s.name in wanted]
        missing = sorted(wanted - {s.name for s in steps})
        if missing:
            raise SystemExit(f"Unknown step(s): {missing}")

    if not steps:
        print("[run_all] no steps registered; nothing to do", flush=True)
        return 0

    cache = _load_cache()
    cache_steps = cache.get("steps", {})
    if not isinstance(cache_steps, dict):
        cache_steps = {}

    for step in steps:
        script_path = scripts_dir() / step.script
        sig = _step_signature(script_path, step.args)
        ok, _ = _outputs_ok(step)
        cached = cache_steps.get(step.name) == sig
        if ok and cached and not args.force:
            print(f"[run_all] skip step={step.name} (cached)", flush=True)
            continue
        _run_step(step)
        cache_steps[step.name] = sig
        cache["steps"] = cache_steps
        _write_cache(cache)

    print("[run_all] all steps completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

