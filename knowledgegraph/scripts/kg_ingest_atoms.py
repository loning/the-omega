#!/usr/bin/env python3
"""Ingest LLM task outputs into append-only atom files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from _kg_common import (
    compute_sha256,
    default_kg_root,
    normalize_type,
    scan_atoms,
    slugify,
)

VERSIONED_LABEL_RE = re.compile(r"^(?P<canonical>[a-z0-9-]+)-h(?P<hash>[0-9a-f]{12})$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest task json into atom files.")
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Task path or glob (repeatable). If omitted, use all pending queue files.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Max tasks to ingest")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument(
        "--move-processed",
        action="store_true",
        help="Move consumed tasks to .kgcache/llm_queue/processed",
    )
    return parser.parse_args()


def expand_tasks(kg_root: Path, patterns: Iterable[str]) -> List[Path]:
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
        queue = kg_root / ".kgcache" / "llm_queue"
        if queue.exists():
            out.extend(sorted(queue.glob("task_*.json")))

    return sorted(set(p.resolve() for p in out if p.exists()))


def ensure_unique_label(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base
    idx = 2
    while True:
        cand = f"{base}-v{idx}"
        if cand not in used:
            used.add(cand)
            return cand
        idx += 1


def make_tex_stub(label: str, atom_type: str, task: Dict[str, object]) -> str:
    source_path = str(task.get("source_path") or "")
    diff_excerpt = str(task.get("diff_excerpt") or "")[:1200]
    escaped_excerpt = diff_excerpt.replace("\\", "\\textbackslash ")
    return (
        f"% auto-generated atom\n"
        f"% source: {source_path}\n"
        f"\\paragraph{{{atom_type}}}\\label{{kg:{label}}}\n"
        f"\\textbf{{Source}}: \\texttt{{{source_path}}}\\\\\n"
        f"\\textbf{{Excerpt}}:\n"
        f"\\begin{{verbatim}}\n{escaped_excerpt}\n\\end{{verbatim}}\n"
    )


def canonical_from_atom_label(label: str) -> str:
    matched = VERSIONED_LABEL_RE.match(label)
    if matched:
        return matched.group("canonical")
    return label


def build_latest_label_by_canonical(existing_atoms) -> Dict[str, str]:
    latest: Dict[str, str] = {}
    for atom in sorted(existing_atoms, key=lambda a: a.kg_id):
        latest[canonical_from_atom_label(atom.label)] = atom.label
    return latest


def resolve_parent_labels_for_tex_task(
    task: Dict[str, object], canonical_latest: Dict[str, str]
) -> List[str]:
    refs_obj = task.get("source_refs")
    refs = refs_obj if isinstance(refs_obj, list) else []
    out: List[str] = []
    seen = set()
    for ref in refs:
        text = str(ref).strip()
        if not text:
            continue

        direct = slugify(text)
        if direct in canonical_latest.values() and direct not in seen:
            seen.add(direct)
            out.append(direct)
            continue

        canonical = slugify(text)
        resolved = canonical_latest.get(canonical)
        if resolved and resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


def inject_canonical_kg_label(tex: str, label: str) -> str:
    marker = f"\\label{{kg:{label}}}"
    if marker in tex:
        return tex

    begin_match = re.search(r"\\begin\{[A-Za-z*]+\}", tex)
    if begin_match:
        return tex[: begin_match.end()] + "\n" + marker + tex[begin_match.end() :]
    return marker + "\n" + tex


def finalize_tex_payload(unit_tex: str, label: str, source_path: str) -> bytes:
    payload_text = (
        f"% auto-generated atom\n"
        f"% source: {source_path}\n"
        f"{inject_canonical_kg_label(unit_tex, label)}\n"
    )
    return payload_text.encode("utf-8")


def resolve_payload(task: Dict[str, object], atom_type: str, label: str) -> Tuple[bytes, str]:
    source_path = str(task.get("source_path") or "")
    source = Path(source_path) if source_path else None

    if source and source.exists() and source.is_file() and atom_type in {"tp-method", "tp-artifact"}:
        data = source.read_bytes()
        ext = source.suffix.lstrip(".") or "bin"
        return data, ext

    if source and source.exists() and source.is_file() and source.suffix.lower() != ".tex":
        data = source.read_bytes()
        ext = source.suffix.lstrip(".") or "bin"
        return data, ext

    if source and source.exists() and source.is_file() and source.suffix.lower() == ".tex":
        text = source.read_text(encoding="utf-8", errors="replace")
        if f"\\label{{kg:{label}}}" not in text:
            text = f"\\label{{kg:{label}}}\n" + text
        return text.encode("utf-8"), "tex"

    stub = make_tex_stub(label, atom_type, task)
    return stub.encode("utf-8"), "tex"


def next_kg_id_factory(kg_root: Path, now: datetime):
    date_part = now.strftime("%Y%m%d")
    prefix = f"KG-{date_part}-"
    max_seq = 0
    atoms_dir = kg_root / "atoms"
    if atoms_dir.exists():
        for path in atoms_dir.rglob("*"):
            if not path.is_file():
                continue
            name = path.name
            if not name.startswith(prefix):
                continue
            seq = name[len(prefix) : len(prefix) + 4]
            if seq.isdigit():
                max_seq = max(max_seq, int(seq))

    current = max_seq

    def _next() -> str:
        nonlocal current
        current += 1
        return f"{prefix}{current:04d}"

    return _next


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    atoms_dir = kg_root / "atoms"
    atoms_dir.mkdir(parents=True, exist_ok=True)

    task_paths = expand_tasks(kg_root, args.task)
    if not task_paths:
        print("No task files to ingest.")
        return 1

    existing_atoms, _ = scan_atoms(kg_root)
    used_labels = {a.label for a in existing_atoms}
    canonical_latest = build_latest_label_by_canonical(existing_atoms)
    id_now = datetime.now(timezone.utc)
    next_kg_id = next_kg_id_factory(kg_root, id_now)

    processed_dir = kg_root / ".kgcache" / "llm_queue" / "processed"
    created = 0

    for task_path in task_paths[: args.limit]:
        task = json.loads(task_path.read_text(encoding="utf-8"))
        raw_type = str(task.get("suggested_node_type") or "tp-claim")
        full_type, type_token = normalize_type(raw_type)
        task_kind = str(task.get("task_kind") or "")

        parent_list: List[str]
        payload: bytes
        ext: str
        label: str

        if task_kind == "tex_knowledge_unit":
            unit_tex = str(task.get("unit_tex") or "")
            source_path = str(task.get("source_path") or "")
            canonical = slugify(str(task.get("canonical_label") or "")) or slugify(
                str(task.get("source_tex_label") or "")
            )
            if not canonical:
                canonical = slugify(str(task.get("proposed_label") or "tex-unit"))

            # Stable semantic label for a knowledge unit: canonical source label + unit content hash.
            unit_hash12 = compute_sha256_bytes(unit_tex.encode("utf-8"))[:12]
            label = f"{canonical}-h{unit_hash12}"
            payload = finalize_tex_payload(unit_tex, label, source_path)
            hash12 = compute_sha256_bytes(payload)[:12]

            if label in used_labels:
                print(f"skip existing tex knowledge atom label: {label}")
                if args.move_processed and not args.dry_run:
                    processed_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(task_path), str(processed_dir / task_path.name))
                continue
            used_labels.add(label)

            parent_list = resolve_parent_labels_for_tex_task(task, canonical_latest)
            if not parent_list:
                parent_list = ["root"]

            ext = "tex"
        else:
            proposed = str(task.get("proposed_label") or "")
            base_label = slugify(proposed) if proposed else slugify(
                Path(str(task.get("source_path") or "")).stem
            )
            label = ensure_unique_label(base_label, used_labels)

            parents = task.get("candidate_parent_labels")
            if isinstance(parents, list) and parents:
                parent_list = [slugify(str(x)) for x in parents[:6] if str(x).strip()]
            else:
                parent_list = ["root"]

            if not parent_list:
                parent_list = ["root"]

            payload, ext = resolve_payload(task, full_type, label)
            hash12 = compute_sha256_bytes(payload)[:12]

        kg_id = next_kg_id()

        from_field = "+".join(parent_list) if parent_list != ["root"] else "root"
        filename = f"{kg_id}__lbl-{label}__tp-{type_token}__from-{from_field}__h-{hash12}.{ext}"
        atom_path = atoms_dir / filename

        if args.dry_run:
            print(f"[DRY-RUN] create {atom_path}")
        else:
            atom_path.write_bytes(payload)
            # Validate the hash suffix after write.
            actual = compute_sha256(atom_path)[:12]
            if actual != hash12:
                raise RuntimeError(f"hash mismatch after write: {atom_path}")
            print(f"created {atom_path}")
            canonical_latest[canonical_from_atom_label(label)] = label

        if args.move_processed and not args.dry_run:
            processed_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(task_path), str(processed_dir / task_path.name))

        created += 1

    print(f"Ingested {created} task(s)")
    return 0


def compute_sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
