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
    atom_sidecar_path,
    compact_label,
    compute_sha256,
    default_kg_root,
    normalize_type,
    scan_atoms,
    slugify,
    write_json,
)

VERSIONED_LABEL_RE = re.compile(r"^(?P<canonical>[a-z0-9-]+)-h(?P<hash>[0-9a-f]{12})$")
KG_ID_SEQ_WIDTH = 5


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
    task: Dict[str, object],
    canonical_to_label: Dict[str, str],
    label_to_type: Dict[str, str],
    child_type: str,
    source_label_alias: Dict[str, str] | None = None,
) -> List[str]:
    refs_obj = task.get("source_refs")
    refs = refs_obj if isinstance(refs_obj, list) else []
    out: List[str] = []
    seen = set()
    known_labels = set(canonical_to_label.values())
    for ref in refs:
        text = str(ref).strip()
        if not text:
            continue

        direct = slugify(text)
        if direct in known_labels and direct not in seen:
            seen.add(direct)
            out.append(direct)
            continue

        canonical = slugify(text)
        resolved = canonical_to_label.get(canonical)
        if not resolved:
            resolved = canonical_to_label.get(compact_label(canonical))
        if not resolved and source_label_alias is not None:
            resolved = source_label_alias.get(canonical)
        if resolved and resolved not in seen:
            parent_type = label_to_type.get(resolved, "")
            # Heuristic constraints to reduce semantic back-edges:
            # - definitions should not depend on theorems/corollaries/proofs/remarks.
            if child_type == "tp-def" and parent_type and parent_type != "tp-def":
                continue
            # - remarks should not form note<->note loops.
            if child_type == "tp-note" and parent_type == "tp-note":
                continue
            # - corollaries should not derive directly from other corollaries.
            if child_type == "tp-cor" and parent_type == "tp-cor":
                continue
            seen.add(resolved)
            out.append(resolved)
    return out


def inject_canonical_kg_label(tex: str, label: str) -> str:
    short = compute_sha256_bytes(label.encode("utf-8"))[:12]
    marker = f"\\label{{kgid:{short}}}"
    if marker in tex:
        return tex
    # Inject outside math/theorem environments to avoid amsmath hard errors
    # (e.g. labels inside align* / equation*).
    return f"% kg-label:{label}\n\\phantomsection\n{marker}\n" + tex


def sanitize_tex_unit(tex: str) -> str:
    # Drop standalone TeX conditional-control lines that can become orphaned
    # after source slicing (e.g. trailing \fi without matching \if...).
    drop_line = re.compile(
        r"^\s*\\(?:"
        r"fi|else|or|"
        r"if(?:"
        r"x|num|dim|odd|vmode|hmode|mmode|inner|cat|defined|csname|"
        r"true|false|case|void|hbox|vbox|eof|"
        r")?"
        r")(?=\b|[^A-Za-z@]).*$"
    )
    kept: List[str] = []
    for line in tex.splitlines():
        if drop_line.match(line):
            continue
        kept.append(line)
    out = "\n".join(kept)
    if tex.endswith("\n"):
        out += "\n"
    return out


def wrap_lonely_items(tex: str) -> str:
    has_item = re.search(r"^\s*\\item\b", tex, flags=re.MULTILINE) is not None
    has_list_env = re.search(r"\\begin\{(?:itemize|enumerate|description)\}", tex) is not None
    if has_item and not has_list_env:
        body = tex.rstrip("\n")
        return "\\begin{itemize}\n" + body + "\n\\end{itemize}\n"
    return tex


BEGIN_END_RE = re.compile(r"\\(?P<kind>begin|end)\{(?P<env>[A-Za-z*@]+)\}")
PROOF_BEGIN_RE = re.compile(r"\\begin\s*\{\s*proof\*?\s*\}(?:\[[^\]]*\])?")
PROOF_END_RE = re.compile(r"\\end\s*\{\s*proof\*?\s*\}")
VERB_TOKEN_RE = re.compile(r"\\verb\*?(?P<delim>[^A-Za-z0-9\s])")


def _escape_texttt(text: str) -> str:
    out = text.replace("\\", r"\textbackslash{}")
    out = out.replace("{", r"\{").replace("}", r"\}")
    out = out.replace("%", r"\%").replace("&", r"\&").replace("#", r"\#")
    out = out.replace("_", r"\_")
    return out


def sanitize_unclosed_verb_lines(tex: str) -> str:
    out_lines: List[str] = []
    for raw_line in tex.splitlines(keepends=True):
        line = raw_line
        cursor = 0
        chunks: List[str] = []
        while True:
            m = VERB_TOKEN_RE.search(line, cursor)
            if not m:
                chunks.append(line[cursor:])
                break
            chunks.append(line[cursor : m.start()])
            delim = m.group("delim")
            end = line.find(delim, m.end())
            if end < 0:
                tail = line[m.end() :].strip()
                if tail:
                    chunks.append("\\texttt{" + _escape_texttt(tail[:240]) + "}")
                else:
                    chunks.append("\\texttt{[verbatim]}")
                if line.endswith("\n"):
                    chunks.append("\n")
                break
            chunks.append(line[m.start() : end + 1])
            cursor = end + 1
        out_lines.append("".join(chunks))
    return "".join(out_lines)


def repair_tex_environment_balance(tex: str) -> str:
    out: List[str] = []
    stack: List[str] = []
    last = 0
    for m in BEGIN_END_RE.finditer(tex):
        out.append(tex[last : m.start()])
        kind = m.group("kind")
        env = m.group("env")
        token = m.group(0)
        if kind == "begin":
            stack.append(env)
            out.append(token)
        else:
            if stack and stack[-1] == env:
                stack.pop()
                out.append(token)
            elif env in stack:
                # Close currently-open inner environments first.
                while stack and stack[-1] != env:
                    out.append(f"\\end{{{stack.pop()}}}")
                if stack and stack[-1] == env:
                    stack.pop()
                    out.append(token)
            else:
                # Drop orphan \end{...}.
                pass
        last = m.end()
    out.append(tex[last:])
    while stack:
        out.append(f"\n\\end{{{stack.pop()}}}")
    return "".join(out)


def finalize_tex_payload(unit_tex: str, label: str, source_path: str, unit_env: str = "") -> bytes:
    safe_tex = normalize_tex_fragment(unit_tex, preserve_proof_env=(unit_env == "proof"))
    if unit_env == "label_anchor":
        payload_text = (
            f"% auto-generated label anchor\n"
            f"% source: {source_path}\n"
            f"{safe_tex.rstrip()}\\ignorespaces\n"
        )
    else:
        payload_text = (
            f"% auto-generated atom\n"
            f"% source: {source_path}\n"
            f"{inject_canonical_kg_label(safe_tex, label)}\n"
        )
    return payload_text.encode("utf-8")


def normalize_tex_fragment(tex: str, *, preserve_proof_env: bool = False) -> str:
    safe_tex = sanitize_tex_unit(tex)
    safe_tex = sanitize_unclosed_verb_lines(safe_tex)
    if not preserve_proof_env:
        safe_tex = flatten_proof_environment(safe_tex)
    safe_tex = repair_tex_environment_balance(safe_tex)
    safe_tex = wrap_lonely_items(safe_tex)
    return safe_tex


def flatten_proof_environment(tex: str) -> str:
    text = PROOF_BEGIN_RE.sub(lambda _: "\n\\paragraph{Proof.}\n", tex)
    text = PROOF_END_RE.sub("", text)
    return text


def compute_tex_task_label(task: Dict[str, object]) -> str:
    unit_tex = str(task.get("unit_tex") or "")
    payload_norm_ver = str(task.get("payload_normalizer_version") or "")
    canonical = compact_label(slugify(str(task.get("canonical_label") or ""))) or compact_label(slugify(
        str(task.get("source_tex_label") or "")
    ))
    if not canonical:
        canonical = compact_label(slugify(str(task.get("proposed_label") or "tex-unit")))
    hash_input = unit_tex if not payload_norm_ver else f"{unit_tex}\n% kg-normalizer:{payload_norm_ver}\n"
    unit_hash12 = compute_sha256_bytes(hash_input.encode("utf-8"))[:12]
    return f"{canonical}-h{unit_hash12}"


def truncate_parent_list(parent_list: List[str], max_count: int = 4, max_join_len: int = 96) -> List[str]:
    selected: List[str] = []
    for parent in parent_list:
        if not parent:
            continue
        candidate = selected + [parent]
        if len(candidate) > max_count:
            break
        if len("+".join(candidate)) > max_join_len:
            break
        selected.append(parent)
    return selected


def would_create_cycle(child: str, parent: str, parent_graph: Dict[str, List[str]]) -> bool:
    if child == parent:
        return True
    stack = [parent]
    seen = set()
    while stack:
        cur = stack.pop()
        if cur == child:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(parent_graph.get(cur, []))
    return False


def select_cycle_safe_parents(
    child: str, candidates: List[str], parent_graph: Dict[str, List[str]]
) -> List[str]:
    selected: List[str] = []
    for cand in candidates:
        if would_create_cycle(child, cand, parent_graph):
            continue
        selected.append(cand)
    return selected


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
        text = normalize_tex_fragment(text)
        text = inject_canonical_kg_label(text, label)
        return text.encode("utf-8"), "tex"

    stub = make_tex_stub(label, atom_type, task)
    return stub.encode("utf-8"), "tex"


def merge_task_metadata_into_sidecar(
    *,
    meta_path: Path,
    task: Dict[str, object],
    fallback: Dict[str, object],
) -> None:
    try:
        existing = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        existing = {}
    if not isinstance(existing, dict):
        existing = {}

    merged = dict(existing)
    merged.update(fallback)
    merged["source_path"] = str(task.get("source_path") or merged.get("source_path") or "")
    merged["source_tex_label"] = str(task.get("source_tex_label") or merged.get("source_tex_label") or "")
    merged["canonical_label"] = str(task.get("canonical_label") or merged.get("canonical_label") or "")
    merged["task_id"] = str(task.get("task_id") or merged.get("task_id") or "")
    merged["task_kind"] = str(task.get("task_kind") or merged.get("task_kind") or "")
    merged["merged_sha256"] = str(task.get("merged_sha256") or merged.get("merged_sha256") or "")
    merged["merged_tex_path"] = str(task.get("merged_tex_path") or merged.get("merged_tex_path") or "")
    merged["merged_map_path"] = str(task.get("merged_map_path") or merged.get("merged_map_path") or "")
    merged["unit_fingerprint"] = str(task.get("unit_fingerprint") or merged.get("unit_fingerprint") or "")
    merged["unit_env"] = str(task.get("unit_env") or merged.get("unit_env") or "")
    merged["payload_normalizer_version"] = str(
        task.get("payload_normalizer_version")
        or merged.get("payload_normalizer_version")
        or ""
    )
    merged["extractor_version"] = str(
        task.get("extractor_version") or merged.get("extractor_version") or ""
    )
    write_json(meta_path, merged)


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
            m = re.match(rf"^{re.escape(prefix)}(?P<seq>\d+)", name)
            if m:
                max_seq = max(max_seq, int(m.group("seq")))

    current = max_seq

    def _next() -> str:
        nonlocal current
        current += 1
        return f"{prefix}{current:0{KG_ID_SEQ_WIDTH}d}"

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
    atom_by_label = {a.label: a for a in existing_atoms}
    canonical_latest = build_latest_label_by_canonical(existing_atoms)
    label_to_type = {a.label: a.atom_type for a in existing_atoms}
    parent_graph: Dict[str, List[str]] = {a.label: list(a.parents) for a in existing_atoms}
    source_label_alias: Dict[str, str] = {}
    for atom in existing_atoms:
        meta_path = atom_sidecar_path(atom.path)
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_tex_label = str(meta.get("source_tex_label") or "").strip()
        if source_tex_label:
            source_label_alias[slugify(source_tex_label)] = atom.label
        canonical_label = str(meta.get("canonical_label") or "").strip()
        if canonical_label:
            source_label_alias[slugify(canonical_label)] = atom.label
    id_now = datetime.now(timezone.utc)
    next_kg_id = next_kg_id_factory(kg_root, id_now)

    processed_dir = kg_root / ".kgcache" / "llm_queue" / "processed"
    created = 0

    selected_task_paths = task_paths[: args.limit]

    # Pre-compute canonical->label map for tex knowledge tasks in this ingest batch,
    # so forward references can be resolved even if parent appears later in file order.
    planned_canonical: Dict[str, str] = {}
    planned_label_to_type: Dict[str, str] = {}
    for task_path in selected_task_paths:
        task = json.loads(task_path.read_text(encoding="utf-8"))
        if str(task.get("task_kind") or "") != "tex_knowledge_unit":
            continue
        label = compute_tex_task_label(task)
        planned_canonical[canonical_from_atom_label(label)] = label
        source_tex_label = str(task.get("source_tex_label") or "").strip()
        if source_tex_label:
            source_label_alias[slugify(source_tex_label)] = label
        canonical_label = str(task.get("canonical_label") or "").strip()
        if canonical_label:
            source_label_alias[slugify(canonical_label)] = label
        suggested = str(task.get("suggested_node_type") or "tp-claim")
        full_type, _ = normalize_type(suggested)
        planned_label_to_type[label] = full_type

    for task_path in selected_task_paths:
        task = json.loads(task_path.read_text(encoding="utf-8"))
        raw_type = str(task.get("suggested_node_type") or "tp-claim")
        full_type, type_token = normalize_type(raw_type)
        task_kind = str(task.get("task_kind") or "")
        proof_orphan = False

        parent_list: List[str]
        payload: bytes
        ext: str
        label: str

        if task_kind == "tex_knowledge_unit":
            unit_tex = str(task.get("unit_tex") or "")
            source_path = str(task.get("source_path") or "")
            unit_env = str(task.get("unit_env") or "")
            label = compute_tex_task_label(task)
            payload = finalize_tex_payload(unit_tex, label, source_path, unit_env=unit_env)
            hash12 = compute_sha256_bytes(payload)[:12]

            if label in used_labels:
                print(f"skip existing tex knowledge atom label: {label}")
                if not args.dry_run:
                    existing_atom = atom_by_label.get(label)
                    if existing_atom is not None:
                        merge_task_metadata_into_sidecar(
                            meta_path=atom_sidecar_path(existing_atom.path),
                            task=task,
                            fallback={
                                "kg_id": existing_atom.kg_id,
                                "label": existing_atom.label,
                                "atom_type": existing_atom.atom_type,
                                "parents": list(existing_atom.parents),
                            },
                        )
                if args.move_processed and not args.dry_run:
                    processed_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(task_path), str(processed_dir / task_path.name))
                continue

            merged_lookup = dict(canonical_latest)
            merged_lookup.update(planned_canonical)
            merged_types = dict(label_to_type)
            merged_types.update(planned_label_to_type)
            parent_list = resolve_parent_labels_for_tex_task(
                task, merged_lookup, merged_types, full_type, source_label_alias
            )
            if parent_list:
                parent_list = select_cycle_safe_parents(label, parent_list, parent_graph)
                parent_list = truncate_parent_list(parent_list)
            if not parent_list:
                if full_type == "tp-proof":
                    # Keep proof atoms as roots when no anchor can be resolved.
                    # This preserves merged coverage and allows later repair by
                    # adding better parent links in newer atom versions.
                    print(f"orphan proof atom (fallback root parent): {label}")
                    parent_list = ["root"]
                    proof_orphan = True
                else:
                    parent_list = ["root"]

            used_labels.add(label)

            ext = "tex"
        else:
            proposed = str(task.get("proposed_label") or "")
            base_label = compact_label(
                slugify(proposed)
                if proposed
                else slugify(Path(str(task.get("source_path") or "")).stem)
            )
            label = ensure_unique_label(base_label, used_labels)

            parents = task.get("candidate_parent_labels")
            if isinstance(parents, list) and parents:
                parent_list = [slugify(str(x)) for x in parents[:6] if str(x).strip()]
            else:
                parent_list = ["root"]

            if not parent_list:
                parent_list = ["root"]
            else:
                parent_list = select_cycle_safe_parents(label, parent_list, parent_graph)
                parent_list = truncate_parent_list(parent_list)
                if not parent_list:
                    parent_list = ["root"]

            payload, ext = resolve_payload(task, full_type, label)
            hash12 = compute_sha256_bytes(payload)[:12]

        kg_id = next_kg_id()

        filename = f"{kg_id}__lbl-{label}__tp-{type_token}__h-{hash12}.{ext}"
        atom_path = atoms_dir / filename
        meta_path = atom_sidecar_path(atom_path)

        if args.dry_run:
            print(f"[DRY-RUN] create {atom_path}")
        else:
            atom_path.write_bytes(payload)
            write_json(
                meta_path,
                {
                    "kg_id": kg_id,
                    "label": label,
                    "atom_type": f"tp-{type_token}",
                    "parents": [] if parent_list == ["root"] else parent_list,
                    "source_path": str(task.get("source_path") or ""),
                    "source_tex_label": str(task.get("source_tex_label") or ""),
                    "canonical_label": str(task.get("canonical_label") or ""),
                    "task_id": str(task.get("task_id") or ""),
                    "task_kind": str(task.get("task_kind") or ""),
                    "merged_sha256": str(task.get("merged_sha256") or ""),
                    "merged_tex_path": str(task.get("merged_tex_path") or ""),
                    "merged_map_path": str(task.get("merged_map_path") or ""),
                    "unit_fingerprint": str(task.get("unit_fingerprint") or ""),
                    "unit_env": str(task.get("unit_env") or ""),
                    "extractor_version": str(task.get("extractor_version") or ""),
                    "proof_orphan": bool(proof_orphan),
                },
            )
            # Validate the hash suffix after write.
            actual = compute_sha256(atom_path)[:12]
            if actual != hash12:
                raise RuntimeError(f"hash mismatch after write: {atom_path}")
            print(f"created {atom_path}")
            canonical_latest[canonical_from_atom_label(label)] = label
            label_to_type[label] = f"tp-{type_token}"
            parent_graph[label] = [] if parent_list == ["root"] else list(parent_list)

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
