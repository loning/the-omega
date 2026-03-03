#!/usr/bin/env python3
"""Build index view .tex files from index spec definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Iterable, List, Set

from _kg_common import (
    ancestor_closure,
    default_kg_root,
    normalize_type,
    parse_bool,
    parse_kv_spec,
    scan_atoms,
    tex_input_fragment_status,
    topological_order,
)


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "$": r"\$",
        "&": r"\&",
        "#": r"\#",
        "_": r"\_",
        "%": r"\%",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build index nodes from index specs.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help="Spec path, name, or glob (repeatable). If omitted, use index_specs/*.idx",
    )
    parser.add_argument("--print-path", action="store_true", help="Print output path(s) only")
    return parser.parse_args()


def expand_specs(kg_root: Path, specs: Iterable[str]) -> List[Path]:
    if specs:
        out: List[Path] = []
        for raw in specs:
            p = Path(raw)
            if p.is_absolute() and p.exists():
                out.append(p)
                continue
            matched = list(kg_root.glob(raw))
            if matched:
                out.extend(matched)
                continue
            candidate = kg_root / raw
            if candidate.exists():
                out.append(candidate)
                continue
            named = kg_root / "index_specs" / (raw if raw.endswith(".idx") else f"{raw}.idx")
            if named.exists():
                out.append(named)
        return sorted(set(p.resolve() for p in out))

    spec_dir = kg_root / "index_specs"
    if not spec_dir.exists():
        return []
    return sorted(p.resolve() for p in spec_dir.glob("*.idx"))


def parse_roots(value: str) -> List[str]:
    if not value:
        return []
    out = []
    for part in value.replace(" ", "").split(","):
        if part:
            out.append(part)
    return out


def parse_types(value: str) -> Set[str]:
    if not value:
        return set()
    out: Set[str] = set()
    for item in value.replace(" ", "").split(","):
        if not item:
            continue
        full_type, _ = normalize_type(item)
        out.add(full_type)
    return out


def selection_fingerprint(
    *,
    spec_path: Path,
    roots: List[str],
    include_types: Set[str],
    order: str,
    auto_include_methods: bool,
    ordered_atoms,
    includable_tex_atoms,
    skipped_tex_atoms,
) -> str:
    hasher = hashlib.sha256()
    hasher.update(spec_path.resolve().as_posix().encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(",".join(sorted(roots)).encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(",".join(sorted(include_types)).encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(order.encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(str(bool(auto_include_methods)).encode("utf-8"))
    hasher.update(b"\n")
    for atom in ordered_atoms:
        hasher.update(
            f"{atom.kg_id}|{atom.label}|{atom.atom_type}|{atom.ext}|{atom.hash12}\n".encode("utf-8")
        )
    hasher.update(b"#includable\n")
    for atom in includable_tex_atoms:
        hasher.update(f"{atom.kg_id}\n".encode("utf-8"))
    hasher.update(b"#skipped\n")
    for atom, reason in skipped_tex_atoms:
        hasher.update(f"{atom.kg_id}|{reason}\n".encode("utf-8"))
    return hasher.hexdigest()


def build_single_spec(kg_root: Path, spec_path: Path) -> Path:
    data = parse_kv_spec(spec_path)
    name = data.get("name", spec_path.stem)
    roots = parse_roots(data.get("roots", ""))
    include_types = parse_types(data.get("include_types", ""))
    order = data.get("order", "topo").strip().lower()
    auto_include_methods = parse_bool(data.get("auto_include_methods", "false"), default=False)

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    if scan_errors:
        raise RuntimeError("scan errors:\n" + "\n".join(scan_errors))

    by_label = {a.label: a for a in atoms}
    if roots:
        missing = [r for r in roots if r not in by_label]
        if missing:
            raise RuntimeError(f"roots missing in atom graph for {spec_path}: {missing}")
        selected_labels = ancestor_closure(roots, by_label)
    else:
        selected_labels = set(by_label.keys())

    selected_atoms = [a for a in atoms if a.label in selected_labels]
    if include_types:
        selected_atoms = [a for a in selected_atoms if a.atom_type in include_types]

    if not auto_include_methods:
        selected_atoms = [a for a in selected_atoms if a.atom_type != "tp-method"]

    if order == "topo":
        ordered = topological_order(atoms, subset={a.label for a in selected_atoms})
    elif order == "alpha":
        ordered = sorted(selected_atoms, key=lambda a: a.label)
    else:
        raise ValueError(f"unsupported order {order} in {spec_path}")

    tex_atoms = [a for a in ordered if a.ext == "tex"]
    non_tex_atoms = [a for a in ordered if a.ext != "tex"]
    includable_tex_atoms = []
    skipped_tex_atoms = []
    for atom in tex_atoms:
        ok, reason = tex_input_fragment_status(atom.path)
        if ok:
            includable_tex_atoms.append(atom)
        else:
            skipped_tex_atoms.append((atom, reason or "not input-fragment safe"))

    out_dir = kg_root / "index_nodes" / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tex = out_dir / f"idx_{name}_main.tex"
    alias_dir = out_dir / "atoms"
    manifest_path = out_dir / "manifest.json"

    fingerprint = selection_fingerprint(
        spec_path=spec_path,
        roots=roots,
        include_types=include_types,
        order=order,
        auto_include_methods=auto_include_methods,
        ordered_atoms=ordered,
        includable_tex_atoms=includable_tex_atoms,
        skipped_tex_atoms=skipped_tex_atoms,
    )
    if manifest_path.exists() and out_tex.exists() and alias_dir.exists():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_manifest = {}
        if previous_manifest.get("selection_fingerprint") == fingerprint:
            return out_tex

    if alias_dir.exists():
        shutil.rmtree(alias_dir)
    alias_dir.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("% Auto-generated by kg_build_index.py")
    lines.append(f"% spec: {spec_path}")
    lines.append(f"\\section*{{Index: {latex_escape(name)}}}")
    lines.append("\\subsection*{Included TeX Atoms}")

    if includable_tex_atoms:
        for atom in includable_tex_atoms:
            alias_name = f"{atom.kg_id}.tex"
            alias_path = alias_dir / alias_name
            src_path = atom.path.resolve()
            try:
                alias_path.symlink_to(src_path)
            except OSError:
                shutil.copy2(src_path, alias_path)
            tex_path = (Path("atoms") / alias_name).as_posix()
            lines.append(f"% {atom.kg_id} {atom.label} {atom.atom_type}")
            lines.append(f"\\kginput{{{tex_path}}}")
    else:
        lines.append("\\emph{No TeX atoms selected.}")

    lines.append("\\subsection*{Skipped Root TeX Atoms}")
    if skipped_tex_atoms:
        lines.append("\\begin{itemize}")
        for atom, reason in skipped_tex_atoms:
            lines.append(
                "\\item "
                f"\\texttt{{{atom.kg_id}}} ({atom.atom_type}) "
                f"label=\\texttt{{{atom.label}}}, reason=\\texttt{{{latex_escape(reason)}}}"
            )
        lines.append("\\end{itemize}")
    else:
        lines.append("\\emph{None.}")

    lines.append("\\subsection*{Non-TeX Atoms}")
    if non_tex_atoms:
        lines.append("\\begin{itemize}")
        for atom in non_tex_atoms:
            lines.append(
                f"\\item \\texttt{{{atom.kg_id}}} ({atom.atom_type}) label=\\texttt{{{atom.label}}}"
            )
        lines.append("\\end{itemize}")
    else:
        lines.append("\\emph{None.}")

    out_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "name": name,
        "spec": str(spec_path),
        "roots": roots,
        "include_types": sorted(include_types),
        "selection_fingerprint": fingerprint,
        "atom_count": len(ordered),
        "tex_atom_count": len(tex_atoms),
        "includable_tex_atom_count": len(includable_tex_atoms),
        "skipped_root_tex_atom_count": len(skipped_tex_atoms),
        "non_tex_atom_count": len(non_tex_atoms),
        "output_tex": str(out_tex),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return out_tex


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    spec_paths = expand_specs(kg_root, args.spec)
    if not spec_paths:
        print("No index spec files found.")
        return 1

    outputs: List[Path] = []
    for spec in spec_paths:
        out = build_single_spec(kg_root, spec)
        outputs.append(out)

    if args.print_path:
        for out in outputs:
            print(out)
    else:
        for out in outputs:
            print(f"generated {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
