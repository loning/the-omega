#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Content-addressed artifact directories + manifest writing."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from common_hash import git_head_sha, python_runtime, sha256_file, sha256_json
from common_paths import artifacts_dir, paper_root


@dataclass(frozen=True)
class RunInfo:
    experiment: str
    run_id: str
    run_dir: Path
    cached: bool


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def make_run_id(
    experiment: str,
    params: Dict[str, Any],
    script_path: Path,
    extra_fingerprint: Optional[Dict[str, Any]] = None,
) -> str:
    payload: Dict[str, Any] = {
        "experiment": experiment,
        "params": params,
        "script_sha256": sha256_file(script_path),
    }
    if extra_fingerprint is not None:
        payload["extra"] = extra_fingerprint
    return sha256_json(payload)[:16]


def manifest_path(run_dir: Path) -> Path:
    return run_dir / "manifest.json"


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    p = manifest_path(run_dir)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_manifest(run_dir: Path, manifest: Dict[str, Any]) -> None:
    p = manifest_path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    p.write_text(txt, encoding="utf-8")


def prepare_run(
    experiment: str,
    params: Dict[str, Any],
    script_path: Path,
    required_files: Optional[Iterable[str]] = None,
    force: bool = False,
    extra_fingerprint: Optional[Dict[str, Any]] = None,
) -> RunInfo:
    run_id = make_run_id(experiment, params=params, script_path=script_path, extra_fingerprint=extra_fingerprint)
    run_dir = artifacts_dir() / experiment / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    cached = False
    if not force:
        cached = True
        if required_files is not None:
            for rel in required_files:
                if not (run_dir / rel).is_file():
                    cached = False
                    break
        if not manifest_path(run_dir).is_file():
            cached = False

    return RunInfo(experiment=experiment, run_id=run_id, run_dir=run_dir, cached=cached)


def build_base_manifest(experiment: str, run_id: str, params: Dict[str, Any], script_path: Path) -> Dict[str, Any]:
    return {
        "version": 1,
        "experiment": experiment,
        "run_id": run_id,
        "created_at": _now_iso(),
        "paper_root": str(paper_root()),
        "git_head": git_head_sha(paper_root()),
        "python": python_runtime(),
        "script": str(Path(script_path).name),
        "script_sha256": sha256_file(script_path),
        "params": params,
        "outputs": [],
    }


def add_output_hashes(manifest: Dict[str, Any], run_dir: Path, rel_paths: List[str]) -> Dict[str, Any]:
    outs: List[Dict[str, Any]] = []
    for rel in rel_paths:
        p = run_dir / rel
        if p.is_file():
            outs.append({"path": rel, "sha256": sha256_file(p), "bytes": int(p.stat().st_size)})
        else:
            outs.append({"path": rel, "sha256": "", "bytes": 0})
    m2 = dict(manifest)
    m2["outputs"] = outs
    return m2

