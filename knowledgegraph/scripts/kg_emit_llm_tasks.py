#!/usr/bin/env python3
"""Convert source deltas into LLM task files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List

from _kg_common import (
    compact_label,
    default_kg_root,
    now_utc_compact,
    scan_atoms,
    slugify,
)
try:
    from pylatexenc.latexwalker import LatexEnvironmentNode, LatexMacroNode, LatexWalker
except ImportError:
    LatexEnvironmentNode = None
    LatexMacroNode = None
    LatexWalker = None

ENV_TO_TYPE = {
    "definition": "tp-def",
    "axiom": "tp-axiom",
    "lemma": "tp-lemma",
    "theorem": "tp-thm",
    "corollary": "tp-cor",
    "proposition": "tp-prop",
    "claim": "tp-claim",
    "conjecture": "tp-conj",
    "proof": "tp-proof",
    "example": "tp-exp",
    "remark": "tp-note",
    "algorithm": "tp-method",
    "equation": "tp-claim",
    "align": "tp-claim",
}

ENV_NAMES = sorted(ENV_TO_TYPE.keys(), key=len, reverse=True)
ANCHOR_ENV_TYPES = {k for k in ENV_TO_TYPE.keys() if k != "proof"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit LLM tasks from source delta files.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--delta",
        action="append",
        default=[],
        help="Delta file path or glob (repeatable). If omitted, uses latest deltas per source.",
    )
    parser.add_argument(
        "--max-per-delta",
        type=int,
        default=1000,
        help="Maximum tasks to emit per delta file",
    )
    return parser.parse_args()


def expand_delta_paths(kg_root: Path, patterns: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    if patterns:
        for pat in patterns:
            p = Path(pat)
            if p.is_absolute() and p.exists():
                out.append(p)
                continue
            matched = list(kg_root.glob(pat))
            if matched:
                out.extend(matched)
                continue
            candidate = kg_root / pat
            if candidate.exists():
                out.append(candidate)
    else:
        source_root = kg_root / ".kgcache" / "source"
        if source_root.exists():
            for source_dir in sorted(source_root.iterdir()):
                if not source_dir.is_dir():
                    continue
                deltas = sorted(source_dir.glob("delta_*.jsonl"))
                if deltas:
                    out.append(deltas[-1])

    return sorted(set(p.resolve() for p in out if p.exists()))


def suggested_type(change_type: str, path: str) -> str:
    if change_type == "deleted":
        return "tp-errata"

    ext = Path(path).suffix.lower()
    if ext in {".py", ".sh", ".ipynb"}:
        return "tp-method"
    if ext in {".csv", ".json", ".yaml", ".yml", ".tsv", ".log", ".txt"}:
        return "tp-artifact"
    if ext == ".tex":
        if "/generated/" in path.replace("\\", "/"):
            return "tp-artifact"
        return "tp-claim"
    return "tp-artifact"


def read_excerpt(path: Path, max_chars: int = 2000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:max_chars]


def read_full_text(path: Path, max_chars: int = 2_000_000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:max_chars]


def tokenize(text: str) -> List[str]:
    return [t for t in slugify(text).split("-") if t]


def find_candidate_labels(path: str, atom_labels: List[str], top_k: int = 6) -> List[str]:
    path_tokens = set(tokenize(Path(path).stem) + tokenize(path))
    scored = []
    for label in atom_labels:
        label_tokens = set(label.split("-"))
        score = len(path_tokens & label_tokens)
        if score > 0:
            scored.append((score, label))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [label for _, label in scored[:top_k]]


def load_delta_records(delta_path: Path) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for line in delta_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def split_ref_labels(raw: str) -> List[str]:
    out = []
    for part in raw.split(","):
        label = part.strip()
        if label:
            out.append(label)
    return out


def unique_keep_order(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _macro_first_arg_text(node) -> str:
    if not LatexMacroNode or not isinstance(node, LatexMacroNode):
        return ""
    if not node.nodeargd or not node.nodeargd.argnlist:
        return ""
    arg0 = node.nodeargd.argnlist[0]
    if arg0 is None or not hasattr(arg0, "latex_verbatim"):
        return ""
    text = arg0.latex_verbatim()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    return text.strip()


def _iter_nodes_recursive(nodes):
    for node in nodes or []:
        yield node
        # Dive into normal child nodes.
        if hasattr(node, "nodelist") and node.nodelist:
            yield from _iter_nodes_recursive(node.nodelist)
        # Dive into macro arguments where refs/labels may appear.
        if LatexMacroNode and isinstance(node, LatexMacroNode) and node.nodeargd:
            for arg in node.nodeargd.argnlist:
                if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                    yield from _iter_nodes_recursive(arg.nodelist)


def _collect_labels_refs(env_node) -> tuple[List[str], List[str]]:
    labels: List[str] = []
    refs: List[str] = []
    for node in _iter_nodes_recursive(getattr(env_node, "nodelist", None)):
        if not LatexMacroNode or not isinstance(node, LatexMacroNode):
            continue
        macro = node.macroname
        arg = _macro_first_arg_text(node)
        if not arg:
            continue
        if macro == "label":
            labels.append(arg)
        elif macro in {"ref", "eqref", "autoref", "cref", "Cref"}:
            refs.extend(split_ref_labels(arg))
    return unique_keep_order(labels), unique_keep_order(refs)


def _iter_environment_nodes(nodes):
    for node in nodes or []:
        if LatexEnvironmentNode and isinstance(node, LatexEnvironmentNode):
            yield node
        if hasattr(node, "nodelist") and node.nodelist:
            yield from _iter_environment_nodes(node.nodelist)
        if LatexMacroNode and isinstance(node, LatexMacroNode) and node.nodeargd:
            for arg in node.nodeargd.argnlist:
                if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                    yield from _iter_environment_nodes(arg.nodelist)


def extract_tex_knowledge_units(tex: str, source_stem: str) -> List[Dict[str, object]]:
    if LatexWalker is None:
        raise RuntimeError(
            "pylatexenc is required for TeX atom extraction. "
            "Install with: python3 -m pip install --user --break-system-packages pylatexenc"
        )

    walker = LatexWalker(tex)
    root_nodes, _, _ = walker.get_latex_nodes(pos=0)
    units: List[Dict[str, object]] = []

    env_nodes = sorted(
        list(_iter_environment_nodes(root_nodes)),
        key=lambda node: getattr(node, "pos", 0),
    )
    last_anchor_ref = ""
    for env_node in env_nodes:
        env_raw = env_node.environmentname or ""
        env_base = env_raw[:-1] if env_raw.endswith("*") else env_raw
        if env_base not in ENV_TO_TYPE:
            continue

        block = tex[env_node.pos : env_node.pos + env_node.len]
        labels, refs = _collect_labels_refs(env_node)
        source_label = labels[0] if labels else ""
        canonical = compact_label(
            slugify(source_label)
            if source_label
            else slugify(f"{source_stem}-{env_base}-{len(units) + 1:04d}")
        )
        if env_base == "proof":
            if not refs and last_anchor_ref:
                refs = [last_anchor_ref]
            # Drop orphan proofs: proof atoms must be attached to a statement atom.
            if not refs:
                continue
        units.append(
            {
                "env": env_base,
                "node_type": ENV_TO_TYPE[env_base],
                "source_label": source_label,
                "canonical_label": canonical,
                "source_refs": refs,
                "unit_tex": block,
            }
        )
        if env_base in ANCHOR_ENV_TYPES:
            last_anchor_ref = source_label or canonical

    return units


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)

    delta_paths = expand_delta_paths(kg_root, args.delta)
    if not delta_paths:
        print("No delta files found.")
        return 1

    atoms, _ = scan_atoms(kg_root)
    atom_labels = sorted([a.label for a in atoms])

    queue_dir = kg_root / ".kgcache" / "llm_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    emitted = 0
    ts = now_utc_compact()

    for delta_path in delta_paths:
        records = load_delta_records(delta_path)
        emitted_for_delta = 0
        for idx, rec in enumerate(records, start=1):
            if emitted_for_delta >= args.max_per_delta:
                break
            change_type = str(rec.get("change_type", ""))
            path = str(rec.get("path") or rec.get("new_path") or "")
            source_path = path
            source_file = Path(path) if path else None
            excerpt = read_excerpt(source_file) if source_file else ""
            s_type = suggested_type(change_type, path)
            new_hash = rec.get("new_hash")
            old_hash = rec.get("old_hash")
            suffix_hash = str(new_hash or old_hash or "")[:12]
            base_label = compact_label(slugify(Path(path).stem if path else f"change-{idx}"))
            proposed_label = f"{base_label}-{suffix_hash}" if suffix_hash else base_label

            # For source TeX files, emit one task per knowledge unit (theorem/lemma/...).
            if (
                source_file
                and change_type in {"added", "modified", "renamed"}
                and source_file.suffix.lower() == ".tex"
                and "/generated/" not in source_file.as_posix()
            ):
                tex = read_full_text(source_file)
                units = extract_tex_knowledge_units(tex, source_file.stem)
                if units:
                    for uidx, unit in enumerate(units, start=1):
                        if emitted_for_delta >= args.max_per_delta:
                            break
                        unit_hash = hashlib.sha256(str(unit["unit_tex"]).encode("utf-8")).hexdigest()[:12]
                        unit_proposed = (
                            f"{unit['canonical_label']}-{unit_hash}"
                            if unit_hash
                            else str(unit["canonical_label"])
                        )
                        task = {
                            "task_id": f"TASK-{ts}-{emitted + 1:06d}",
                            "created_at": ts,
                            "delta_file": str(delta_path),
                            "source_name": rec.get("source_name"),
                            "change_type": change_type,
                            "source_path": source_path,
                            "old_hash": old_hash,
                            "new_hash": new_hash,
                            "diff_excerpt": str(unit["unit_tex"])[:2000],
                            "candidate_parent_labels": [slugify(r) for r in unit["source_refs"]],
                            "suggested_node_type": unit["node_type"],
                            "proposed_label": unit_proposed,
                            "status": "pending",
                            "task_kind": "tex_knowledge_unit",
                            "unit_index": uidx,
                            "unit_env": unit["env"],
                            "canonical_label": unit["canonical_label"],
                            "source_tex_label": unit["source_label"],
                            "source_refs": unit["source_refs"],
                            "unit_tex": unit["unit_tex"],
                        }
                        task_path = queue_dir / f"task_{ts}_{emitted + 1:06d}.json"
                        task_path.write_text(
                            json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8"
                        )
                        emitted += 1
                        emitted_for_delta += 1
                    continue

            task = {
                "task_id": f"TASK-{ts}-{emitted + 1:06d}",
                "created_at": ts,
                "delta_file": str(delta_path),
                "source_name": rec.get("source_name"),
                "change_type": change_type,
                "source_path": source_path,
                "old_hash": old_hash,
                "new_hash": new_hash,
                "diff_excerpt": excerpt,
                "candidate_parent_labels": find_candidate_labels(source_path, atom_labels),
                "suggested_node_type": s_type,
                "proposed_label": proposed_label,
                "status": "pending",
            }

            task_path = queue_dir / f"task_{ts}_{emitted + 1:06d}.json"
            task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
            emitted += 1
            emitted_for_delta += 1

    print(f"Emitted {emitted} task(s) into {queue_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
