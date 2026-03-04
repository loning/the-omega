#!/usr/bin/env python3
"""Visualize atom DAG as Graphviz dot/svg and export edge list."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from _kg_common import Atom, default_kg_root, scan_atoms, topological_order

KG_ID_RE = re.compile(r"^KG-(?P<date>\d{8})-(?P<seq>\d+)$")

TYPE_COLORS = {
    "tp-def": "#e7f5ff",
    "tp-axiom": "#fff3bf",
    "tp-lemma": "#e9fac8",
    "tp-thm": "#d3f9d8",
    "tp-prop": "#d0ebff",
    "tp-cor": "#c5f6fa",
    "tp-claim": "#f3d9fa",
    "tp-conj": "#ffe3e3",
    "tp-proof": "#f1f3f5",
    "tp-note": "#fff4e6",
    "tp-exp": "#e6fcf5",
    "tp-method": "#ede7f6",
    "tp-artifact": "#f8f0fc",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize DAG from knowledgegraph atoms.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=480,
        help="Max nodes in sampled atom graph",
    )
    parser.add_argument(
        "--sample-seeds",
        type=int,
        default=120,
        help="Seed count (latest KG IDs) when --sample-root is not given",
    )
    parser.add_argument(
        "--sample-root",
        action="append",
        default=[],
        help="Root atom label for sample graph (repeatable)",
    )
    parser.add_argument(
        "--no-sample-ancestors",
        action="store_true",
        help="Do not expand ancestor closure from sample seeds",
    )
    parser.add_argument(
        "--emit-full-dot",
        action="store_true",
        help="Emit full atom graph dot (large file)",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip Graphviz rendering and keep dot only",
    )
    return parser.parse_args()


def kg_id_sort_key(kg_id: str) -> Tuple[str, int]:
    m = KG_ID_RE.match(kg_id)
    if not m:
        return "", -1
    return m.group("date"), int(m.group("seq"))


def graphviz_node_id(label: str, idx: int) -> str:
    return f"n{idx:06d}"


def quote_dot(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def shorten(text: str, max_len: int = 58) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def color_for_type(atom_type: str) -> str:
    if atom_type in TYPE_COLORS:
        return TYPE_COLORS[atom_type]
    palette = ["#e3fafc", "#f4fce3", "#fff3bf", "#ffe8cc", "#f8f0fc", "#e9ecef"]
    return palette[hash(atom_type) % len(palette)]


def run_dot(dot_path: Path, fmt: str) -> Path:
    output = dot_path.with_suffix(f".{fmt}")
    subprocess.run(
        ["dot", f"-T{fmt}", str(dot_path), "-o", str(output)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return output


def build_type_graph(atoms: Sequence[Atom]) -> str:
    node_counts = Counter(a.atom_type for a in atoms)
    edge_counts = Counter()
    atom_type_by_label = {a.label: a.atom_type for a in atoms}

    for atom in atoms:
        for parent in atom.parents:
            parent_type = atom_type_by_label.get(parent)
            if parent_type is None:
                continue
            edge_counts[(atom.atom_type, parent_type)] += 1

    lines: List[str] = []
    lines.append("digraph KGTypeDAG {")
    lines.append("  graph [rankdir=LR, overlap=false, splines=true, pad=0.2];")
    lines.append('  node [shape=box, style="rounded,filled", fontname="Helvetica"];')
    lines.append('  edge [fontname="Helvetica", color="#4c6ef5"];')

    for atom_type in sorted(node_counts):
        count = node_counts[atom_type]
        label = f"{atom_type}\\nN={count}"
        fill = color_for_type(atom_type)
        lines.append(
            f"  {quote_dot(atom_type)} [label={quote_dot(label)}, fillcolor={quote_dot(fill)}];"
        )

    for (child_type, parent_type), count in sorted(
        edge_counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    ):
        width = 1.0 + math.log10(max(1, count))
        lines.append(
            "  "
            + f"{quote_dot(child_type)} -> {quote_dot(parent_type)} "
            + f"[label={quote_dot(str(count))}, penwidth={width:.2f}];"
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def pick_sample_labels(
    atoms: Sequence[Atom],
    sample_size: int,
    sample_seed_count: int,
    explicit_roots: Sequence[str],
    include_ancestors: bool,
) -> Tuple[Set[str], List[str], List[str]]:
    by_label = {a.label: a for a in atoms}
    atoms_desc = sorted(atoms, key=lambda a: kg_id_sort_key(a.kg_id), reverse=True)

    warnings: List[str] = []
    if explicit_roots:
        seeds = []
        for label in explicit_roots:
            if label in by_label:
                seeds.append(label)
            else:
                warnings.append(f"sample root not found: {label}")
    else:
        seeds = [a.label for a in atoms_desc[: max(0, sample_seed_count)]]

    selected: Set[str] = set()
    stack: List[str] = []
    for lb in seeds:
        if lb in by_label and lb not in selected:
            selected.add(lb)
            stack.append(lb)

    if include_ancestors:
        while stack and len(selected) < sample_size:
            cur = stack.pop()
            atom = by_label.get(cur)
            if atom is None:
                continue
            for parent in atom.parents:
                if parent not in by_label or parent in selected:
                    continue
                selected.add(parent)
                stack.append(parent)
                if len(selected) >= sample_size:
                    break

    if len(selected) < sample_size:
        for atom in atoms_desc:
            if atom.label in selected:
                continue
            selected.add(atom.label)
            if len(selected) >= sample_size:
                break

    return selected, seeds, warnings


def build_sample_atom_graph(atoms: Sequence[Atom], selected_labels: Set[str]) -> str:
    subset_atoms = [a for a in atoms if a.label in selected_labels]
    ordered = topological_order(atoms, subset=selected_labels)
    ordered_labels = [a.label for a in ordered]

    node_id_by_label = {
        label: graphviz_node_id(label, idx) for idx, label in enumerate(ordered_labels, start=1)
    }
    by_label = {a.label: a for a in subset_atoms}
    indegree = {a.label: 0 for a in subset_atoms}
    edge_count = 0
    for atom in subset_atoms:
        for parent in atom.parents:
            if parent in indegree:
                indegree[parent] += 1
                edge_count += 1

    lines: List[str] = []
    lines.append("digraph KGAtomSampleDAG {")
    lines.append("  graph [rankdir=LR, overlap=false, splines=true, pad=0.2];")
    lines.append('  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];')
    lines.append('  edge [color="#495057", arrowsize=0.7];')

    for label in ordered_labels:
        atom = by_label[label]
        node_id = node_id_by_label[label]
        root_like = len(atom.parents) == 0
        fill = color_for_type(atom.atom_type)
        shape = "box3d" if root_like else "box"
        border = "#2f9e44" if root_like else "#495057"
        node_label = f"{shorten(label)}\\n{atom.atom_type}"
        lines.append(
            "  "
            + f"{node_id} [label={quote_dot(node_label)}, fillcolor={quote_dot(fill)}, "
            + f"shape={shape}, color={quote_dot(border)}];"
        )

    for atom in ordered:
        child_id = node_id_by_label[atom.label]
        for parent in atom.parents:
            parent_id = node_id_by_label.get(parent)
            if parent_id is None:
                continue
            lines.append(f"  {child_id} -> {parent_id};")

    lines.append("}")
    _ = edge_count
    return "\n".join(lines) + "\n"


def build_full_atom_graph_dot(atoms: Sequence[Atom]) -> str:
    ordered = topological_order(atoms)
    node_id_by_label = {
        atom.label: graphviz_node_id(atom.label, idx) for idx, atom in enumerate(ordered, start=1)
    }
    lines: List[str] = []
    lines.append("digraph KGAtomFullDAG {")
    lines.append("  graph [rankdir=LR, overlap=false, splines=true, pad=0.1];")
    lines.append('  node [shape=point, width=0.03, height=0.03, label="", color="#868e96"];')
    lines.append('  edge [color="#adb5bd", arrowsize=0.35, penwidth=0.4];')
    for atom in ordered:
        node_id = node_id_by_label[atom.label]
        lines.append(f"  {node_id};")
    for atom in ordered:
        child_id = node_id_by_label[atom.label]
        for parent in atom.parents:
            parent_id = node_id_by_label.get(parent)
            if parent_id is None:
                continue
            lines.append(f"  {child_id} -> {parent_id};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_full_edge_csv(path: Path, atoms: Sequence[Atom]) -> int:
    by_label = {a.label: a for a in atoms}
    edge_count = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "child_label",
                "child_type",
                "child_kg_id",
                "parent_label",
                "parent_type",
                "parent_kg_id",
            ]
        )
        for atom in atoms:
            for parent in atom.parents:
                parent_atom = by_label.get(parent)
                if parent_atom is None:
                    continue
                writer.writerow(
                    [
                        atom.label,
                        atom.atom_type,
                        atom.kg_id,
                        parent_atom.label,
                        parent_atom.atom_type,
                        parent_atom.kg_id,
                    ]
                )
                edge_count += 1
    return edge_count


def write_node_csv(path: Path, atoms: Sequence[Atom]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["label", "atom_type", "kg_id", "parent_count", "file"])
        for atom in sorted(atoms, key=lambda a: kg_id_sort_key(a.kg_id)):
            writer.writerow([atom.label, atom.atom_type, atom.kg_id, len(atom.parents), atom.path.name])


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    out_dir = args.out_dir.resolve() if args.out_dir else (kg_root / ".kgcache" / "visuals")
    out_dir.mkdir(parents=True, exist_ok=True)

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        print("scan errors:")
        for err in scan_errors:
            print(f"- {err}")
        return 2
    if not atoms:
        print("No atoms found.")
        return 1

    edge_count = sum(len(a.parents) for a in atoms)
    root_count = sum(1 for a in atoms if not a.parents)
    type_counts = Counter(a.atom_type for a in atoms)
    type_edge_counts = Counter()
    by_label = {a.label: a for a in atoms}
    for atom in atoms:
        for parent in atom.parents:
            parent_atom = by_label.get(parent)
            if parent_atom is None:
                continue
            type_edge_counts[(atom.atom_type, parent_atom.atom_type)] += 1

    type_dot = out_dir / "dag_types.dot"
    type_dot.write_text(build_type_graph(atoms), encoding="utf-8")

    selected_labels, seeds, sample_warnings = pick_sample_labels(
        atoms=atoms,
        sample_size=max(1, args.sample_size),
        sample_seed_count=max(1, args.sample_seeds),
        explicit_roots=args.sample_root,
        include_ancestors=not args.no_sample_ancestors,
    )
    sample_dot = out_dir / "dag_atoms_sample.dot"
    sample_dot.write_text(build_sample_atom_graph(atoms, selected_labels), encoding="utf-8")

    full_dot = None
    if args.emit_full_dot:
        full_dot = out_dir / "dag_atoms_full.dot"
        full_dot.write_text(build_full_atom_graph_dot(atoms), encoding="utf-8")

    node_csv = out_dir / "dag_nodes.csv"
    edge_csv = out_dir / "dag_edges.csv"
    write_node_csv(node_csv, atoms)
    csv_edge_count = write_full_edge_csv(edge_csv, atoms)

    rendered: List[str] = []
    if not args.no_render:
        for dot_path in [type_dot, sample_dot]:
            for fmt in ("svg", "png"):
                try:
                    out = run_dot(dot_path, fmt)
                    rendered.append(str(out))
                except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                    print(f"render failed for {dot_path.name} ({fmt}): {exc}")
        if full_dot is not None:
            try:
                out = run_dot(full_dot, "svg")
                rendered.append(str(out))
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                print(f"render failed for {full_dot.name} (svg): {exc}")

    summary = {
        "kg_root": str(kg_root),
        "node_count": len(atoms),
        "edge_count": edge_count,
        "root_count": root_count,
        "type_counts": dict(sorted(type_counts.items())),
        "top_type_edges": [
            {"child_type": c, "parent_type": p, "count": n}
            for (c, p), n in type_edge_counts.most_common(32)
        ],
        "sample_size": len(selected_labels),
        "sample_seed_count": len(seeds),
        "sample_seeds": seeds[:64],
        "sample_warnings": sample_warnings,
        "outputs": {
            "type_dot": str(type_dot),
            "sample_dot": str(sample_dot),
            "full_dot": str(full_dot) if full_dot else "",
            "node_csv": str(node_csv),
            "edge_csv": str(edge_csv),
            "rendered": rendered,
        },
        "csv_edge_count": csv_edge_count,
    }
    summary_path = out_dir / "dag_visualization_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"output_dir: {out_dir}")
    print(f"node_count: {len(atoms)}")
    print(f"edge_count: {edge_count}")
    print(f"type_dot: {type_dot}")
    print(f"sample_dot: {sample_dot}")
    if full_dot:
        print(f"full_dot: {full_dot}")
    print(f"node_csv: {node_csv}")
    print(f"edge_csv: {edge_csv} ({csv_edge_count} edges)")
    print(f"summary_json: {summary_path}")
    if rendered:
        print("rendered:")
        for item in rendered:
            print(f"- {item}")
    if sample_warnings:
        print("sample warnings:")
        for warn in sample_warnings:
            print(f"- {warn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
