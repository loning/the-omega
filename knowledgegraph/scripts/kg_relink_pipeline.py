#!/usr/bin/env python3
"""One-shot pipeline: relink DAG, validate, and regenerate visuals/reports."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

from _kg_common import Atom, atom_sidecar_path, default_kg_root, scan_atoms


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run DAG relink + validation + visualization in one command."
    )
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--skip-relink",
        action="store_true",
        help="Skip relink passes and only run validation/visualization",
    )
    parser.add_argument(
        "--skip-full-png",
        action="store_true",
        help="Skip full graph PNG rendering via sfdp",
    )
    parser.add_argument(
        "--skip-component-bridge",
        action="store_true",
        help="Skip synthetic component bridge pass",
    )
    return parser.parse_args()


def run_cmd(cmd: List[str], cwd: Path) -> None:
    print(f"[run] {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}")


def load_meta(atom: Atom) -> Dict[str, object]:
    sidecar = atom_sidecar_path(atom.path)
    if not sidecar.exists():
        return {}
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def compute_connectivity(atoms: List[Atom]) -> Tuple[Dict[str, int], Dict[str, int], List[List[str]]]:
    by_label = {a.label: a for a in atoms}
    labels = set(by_label.keys())
    in_deg = {lb: 0 for lb in labels}
    out_deg = {lb: 0 for lb in labels}
    adj = {lb: set() for lb in labels}

    for atom in atoms:
        for parent in atom.parents:
            if parent not in labels:
                continue
            out_deg[atom.label] += 1
            in_deg[parent] += 1
            adj[atom.label].add(parent)
            adj[parent].add(atom.label)

    seen: Set[str] = set()
    components: List[List[str]] = []
    for label in labels:
        if label in seen:
            continue
        stack = [label]
        seen.add(label)
        comp: List[str] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adj[cur]:
                if nxt in seen:
                    continue
                seen.add(nxt)
                stack.append(nxt)
        components.append(comp)
    components.sort(key=len, reverse=True)
    return in_deg, out_deg, components


def write_connectivity_reports(kg_root: Path) -> Dict[str, object]:
    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        raise RuntimeError("scan failed before connectivity report:\n" + "\n".join(scan_errors[:50]))

    in_deg, out_deg, comps = compute_connectivity(atoms)
    by_label = {a.label: a for a in atoms}
    meta_by_label = {a.label: load_meta(a) for a in atoms}
    isolated = sorted([lb for lb in by_label if in_deg[lb] == 0 and out_deg[lb] == 0])

    isolated_types = Counter(by_label[lb].atom_type for lb in isolated)
    isolated_envs = Counter(str(meta_by_label[lb].get("unit_env") or "") for lb in isolated)

    visuals_dir = kg_root / ".kgcache" / "visuals"
    visuals_dir.mkdir(parents=True, exist_ok=True)

    connectivity_path = visuals_dir / "dag_connectivity_report_after_relink.json"
    connectivity = {
        "nodes": len(atoms),
        "edges": int(sum(out_deg.values())),
        "weak_components": len(comps),
        "largest_component": len(comps[0]) if comps else 0,
        "second_component": len(comps[1]) if len(comps) > 1 else 0,
        "isolated_nodes": len(isolated),
        "isolated_types_top": isolated_types.most_common(20),
        "isolated_envs_top": isolated_envs.most_common(20),
    }
    connectivity_path.write_text(json.dumps(connectivity, ensure_ascii=False, indent=2), encoding="utf-8")

    isolated_csv = visuals_dir / "dag_isolated_nodes.csv"
    with isolated_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["label", "kg_id", "atom_type", "unit_env", "source_tex_label", "proof_orphan"])
        for lb in isolated:
            atom = by_label[lb]
            meta = meta_by_label[lb]
            writer.writerow(
                [
                    lb,
                    atom.kg_id,
                    atom.atom_type,
                    str(meta.get("unit_env") or ""),
                    str(meta.get("source_tex_label") or ""),
                    bool(meta.get("proof_orphan")),
                ]
            )

    return {
        "connectivity_json": str(connectivity_path),
        "isolated_csv": str(isolated_csv),
        "nodes": len(atoms),
        "edges": int(sum(out_deg.values())),
        "weak_components": len(comps),
        "largest_component": len(comps[0]) if comps else 0,
        "isolated_nodes": len(isolated),
    }


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    repo_root = kg_root.parent
    py = sys.executable

    if not args.skip_relink:
        # Phase 1: source-local relink + orphan-proof repair.
        run_cmd(
            [
                py,
                "knowledgegraph/scripts/kg_relink_islands.py",
                "--kg-root",
                str(kg_root),
                "--include-all-isolated",
                "--repair-orphan-proofs",
                "--neighbor-window",
                "600",
                "--max-parents",
                "3",
                "--apply",
            ],
            repo_root,
        )

        # Phase 2: connect remaining islands with controlled global anchors.
        run_cmd(
            [
                py,
                "knowledgegraph/scripts/kg_relink_islands.py",
                "--kg-root",
                str(kg_root),
                "--include-all-isolated",
                "--allow-note-parent-note",
                "--neighbor-window",
                "1200",
                "--max-parents",
                "3",
                "--global-anchor-fallback",
                "--apply",
            ],
            repo_root,
        )

        # Phase 3: strict orphan-proof cleanup (preserve old parents + add statement parent).
        run_cmd(
            [
                py,
                "knowledgegraph/scripts/kg_relink_islands.py",
                "--kg-root",
                str(kg_root),
                "--repair-orphan-proofs",
                "--global-anchor-fallback",
                "--neighbor-window",
                "1200",
                "--max-parents",
                "6",
                "--apply",
            ],
            repo_root,
        )

    if not args.skip_component_bridge:
        run_cmd(
            [
                py,
                "knowledgegraph/scripts/kg_bridge_components.py",
                "--kg-root",
                str(kg_root),
                "--apply",
            ],
            repo_root,
        )

    run_cmd(
        [
            py,
            "knowledgegraph/scripts/kg_upgrade_edge_schema.py",
            "--kg-root",
            str(kg_root),
            "--apply",
        ],
        repo_root,
    )

    run_cmd([py, "knowledgegraph/scripts/kg_check_dag.py", "--kg-root", str(kg_root)], repo_root)
    run_cmd([py, "knowledgegraph/scripts/kg_atom_health_report.py", "--kg-root", str(kg_root)], repo_root)

    run_cmd([py, "knowledgegraph/scripts/kg_visualize_dag.py", "--kg-root", str(kg_root)], repo_root)
    run_cmd(
        [
            py,
            "knowledgegraph/scripts/kg_visualize_dag.py",
            "--kg-root",
            str(kg_root),
            "--emit-full-dot",
            "--no-render",
        ],
        repo_root,
    )
    if not args.skip_full_png:
        run_cmd(
            [
                "sfdp",
                "-Goverlap=prism",
                "-Gsplines=false",
                "-Goutputorder=edgesfirst",
                "-Nshape=point",
                "-Nwidth=0.03",
                "-Nheight=0.03",
                '-Nlabel=',
                "-Ecolor=#adb5bd",
                "-Epenwidth=0.4",
                "-Tpng",
                str(kg_root / ".kgcache" / "visuals" / "dag_atoms_full.dot"),
                "-o",
                str(kg_root / ".kgcache" / "visuals" / "dag_atoms_full_sfdp.png"),
            ],
            repo_root,
        )

    summary = write_connectivity_reports(kg_root)
    print("[done] pipeline completed")
    print(
        "summary: "
        f"nodes={summary['nodes']} edges={summary['edges']} "
        f"components={summary['weak_components']} "
        f"largest={summary['largest_component']} isolated={summary['isolated_nodes']}"
    )
    print(f"connectivity_json: {summary['connectivity_json']}")
    print(f"isolated_csv: {summary['isolated_csv']}")
    print(f"full_png: {kg_root / '.kgcache' / 'visuals' / 'dag_atoms_full_sfdp.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
