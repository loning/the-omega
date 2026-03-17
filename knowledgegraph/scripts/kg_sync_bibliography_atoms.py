#!/usr/bin/env python3
"""Parse source .bib files into append-only atoms and materialize DAG bibliography files."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from _kg_common import (
    atom_sidecar_path,
    compact_label,
    default_kg_root,
    hash12_for_bytes,
    load_source_spec,
    now_utc_compact,
    parallel_kg_id_factory,
    path_matches,
    scan_atoms,
    slugify,
    write_json,
)

KG_ID_RE = re.compile(r"^KG-(?P<date>\d{8})-(?P<seq>\d+)$")
VERSIONED_LABEL_RE = re.compile(r"^(?P<canonical>[a-z0-9-]+)-h(?P<hash>[0-9a-f]{12})$")
CROSSREF_FIELD_RE = re.compile(
    r"(?is)\b(?:crossref|xdata|related)\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^,\n}]+)"
)
KEYLESS_TYPES = {"comment", "preamble", "string"}
SCRIPT_VERSION = "bib-sync-v1"


@dataclass
class BibBlock:
    source_path: Path
    source_rel: str
    block_index: int
    entry_type: str
    cite_key: str
    canonical_label: str
    label: str
    atom_type: str
    payload_text: str
    payload_hash12: str
    crossref_keys: Tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse source bibliography into append-only atom nodes and materialize DAG bibliography files."
    )
    parser.add_argument("--kg-root", type=Path, default=None, help="Knowledgegraph root")
    parser.add_argument(
        "--source-spec",
        default="auric_bibliography",
        help="Source spec path or name under source_specs/ (default: auric_bibliography)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing atoms or bibliography files",
    )
    parser.add_argument(
        "--no-clean-output",
        action="store_true",
        help="Do not delete stale previously-generated bibliography files",
    )
    return parser.parse_args()


def kg_id_sort_key(kg_id: str) -> Tuple[str, int]:
    m = KG_ID_RE.match(kg_id)
    if not m:
        return "", -1
    return m.group("date"), int(m.group("seq"))


def resolve_source_spec_path(kg_root: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute() and p.exists():
        return p.resolve()
    candidate = (kg_root / raw).resolve()
    if candidate.exists():
        return candidate
    named = (kg_root / "source_specs" / (raw if raw.endswith(".src") else f"{raw}.src")).resolve()
    if named.exists():
        return named
    raise RuntimeError(f"source spec not found: {raw}")


def collect_source_bib_files(spec) -> List[Tuple[Path, str]]:
    out: List[Tuple[Path, str]] = []
    for path in sorted(spec.root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(spec.root).as_posix()
        if not path_matches(rel, spec.include):
            continue
        if spec.exclude and path_matches(rel, spec.exclude):
            continue
        if path.suffix.lower() != ".bib":
            continue
        out.append((path.resolve(), rel))
    return out


def find_matching_delim(text: str, start: int, open_ch: str, close_ch: str) -> Optional[int]:
    depth = 0
    in_quote = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_quote = False
            continue
        if ch == '"' and not is_escaped_at(text, idx):
            in_quote = True
            continue
        if ch == open_ch:
            depth += 1
            continue
        if ch == close_ch:
            depth -= 1
            if depth == 0:
                return idx
    return None


def extract_cite_key(body: str, entry_type: str) -> str:
    if entry_type.lower() in KEYLESS_TYPES:
        return ""
    out: List[str] = []
    depth = 0
    in_quote = False
    escaped = False
    for idx, ch in enumerate(body):
        if in_quote:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_quote = False
            continue
        if ch == '"' and not is_escaped_at(body, idx):
            in_quote = True
            out.append(ch)
            continue
        if ch == "{":
            depth += 1
            out.append(ch)
            continue
        if ch == "}":
            depth = max(0, depth - 1)
            out.append(ch)
            continue
        if ch == "," and depth == 0:
            break
        out.append(ch)
    key = "".join(out).strip()
    if key.startswith("{") and key.endswith("}") and len(key) >= 2:
        key = key[1:-1].strip()
    if key.startswith('"') and key.endswith('"') and len(key) >= 2:
        key = key[1:-1].strip()
    return key


def is_escaped_at(text: str, idx: int) -> bool:
    backslashes = 0
    cur = idx - 1
    while cur >= 0 and text[cur] == "\\":
        backslashes += 1
        cur -= 1
    return (backslashes % 2) == 1


def extract_crossref_keys(entry_text: str) -> Tuple[str, ...]:
    out: List[str] = []
    seen = set()
    for m in CROSSREF_FIELD_RE.finditer(entry_text):
        raw = m.group(1).strip()
        if raw.startswith("{") and raw.endswith("}") and len(raw) >= 2:
            raw = raw[1:-1].strip()
        elif raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            raw = raw[1:-1].strip()
        for token in [x.strip() for x in raw.split(",") if x.strip()]:
            if token not in seen:
                seen.add(token)
                out.append(token)
    return tuple(out)


def parse_bib_blocks(source_path: Path, source_rel: str, text: str) -> List[BibBlock]:
    out: List[BibBlock] = []
    idx = 0
    block_index = 0
    while True:
        at = text.find("@", idx)
        if at < 0:
            break
        j = at + 1
        while j < len(text) and text[j].isspace():
            j += 1
        t0 = j
        while j < len(text) and (text[j].isalnum() or text[j] in {"_", "-"}):
            j += 1
        if j == t0:
            idx = at + 1
            continue
        entry_type = text[t0:j].strip().lower()
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] not in {"{", "("}:
            idx = at + 1
            continue
        open_ch = text[j]
        close_ch = "}" if open_ch == "{" else ")"
        end = find_matching_delim(text, j, open_ch, close_ch)
        if end is None:
            break
        raw_block = text[at : end + 1].strip()
        body = text[j + 1 : end]
        cite_key = extract_cite_key(body, entry_type)
        payload_text = raw_block + "\n"
        payload_hash12 = hash12_for_bytes(payload_text.encode("utf-8"))
        if cite_key:
            canonical = compact_label(f"bib-{slugify(cite_key)}")
            atom_type = "tp-bib"
            crossrefs = extract_crossref_keys(payload_text)
        else:
            source_slug = slugify(source_rel.replace("/", "-"))
            canonical = compact_label(f"bibraw-{source_slug}-{block_index:04d}")
            atom_type = "tp-bibraw"
            crossrefs = tuple()
        label = f"{canonical}-h{payload_hash12}"
        out.append(
            BibBlock(
                source_path=source_path,
                source_rel=source_rel,
                block_index=block_index,
                entry_type=entry_type,
                cite_key=cite_key,
                canonical_label=canonical,
                label=label,
                atom_type=atom_type,
                payload_text=payload_text,
                payload_hash12=payload_hash12,
                crossref_keys=crossrefs,
            )
        )
        block_index += 1
        idx = end + 1
    return out


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def existing_latest_bib_label_by_key(kg_root: Path, atoms) -> Dict[str, str]:
    latest: Dict[str, Tuple[Tuple[str, int], str]] = {}
    for atom in atoms:
        if atom.atom_type != "tp-bib":
            continue
        meta = read_json(atom_sidecar_path(atom.path))
        key = slugify(str(meta.get("citation_key") or ""))
        if not key:
            continue
        sort_key = kg_id_sort_key(atom.kg_id)
        prev = latest.get(key)
        if prev is None or sort_key > prev[0]:
            latest[key] = (sort_key, atom.label)
    return {k: v[1] for k, v in latest.items()}


def choose_parent_labels(
    block: BibBlock,
    *,
    local_key_to_label: Dict[str, str],
    global_key_to_label: Dict[str, str],
    existing_key_to_label: Dict[str, str],
) -> List[str]:
    out: List[str] = []
    seen = set()
    for ref_key in block.crossref_keys:
        token = slugify(ref_key)
        parent = (
            local_key_to_label.get(token)
            or global_key_to_label.get(token)
            or existing_key_to_label.get(token)
        )
        if not parent or parent == block.label or parent in seen:
            continue
        seen.add(parent)
        out.append(parent)
    return out


def load_payload_cache(atoms) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for atom in atoms:
        if atom.ext != "bib":
            continue
        try:
            out[atom.label] = atom.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return out


def make_output_name(source_rel: str, used: set[str]) -> str:
    name = Path(source_rel).name
    if name not in used:
        used.add(name)
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix or ".bib"
    counter = 2
    while True:
        candidate = f"{stem}.v{counter}{suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def main() -> int:
    args = parse_args()
    kg_root = args.kg_root.resolve() if args.kg_root else default_kg_root(__file__)
    spec_path = resolve_source_spec_path(kg_root, args.source_spec)
    spec = load_source_spec(spec_path, kg_root)

    source_files = collect_source_bib_files(spec)
    if not source_files:
        print(f"No source .bib files matched: {spec.root}")
        return 0

    atoms_dir = kg_root / "atoms"
    atoms_dir.mkdir(parents=True, exist_ok=True)

    atoms, scan_errors = scan_atoms(kg_root, verify_hash=False)
    filtered_errors = [e for e in scan_errors if "atoms directory not found" not in e]
    if filtered_errors:
        print("scan errors:")
        for err in filtered_errors[:50]:
            print(f"- {err}")
        return 2

    existing_labels = {a.label for a in atoms}
    label_to_payload = load_payload_cache(atoms)
    existing_bib_key_to_label = existing_latest_bib_label_by_key(kg_root, atoms)

    all_blocks: List[BibBlock] = []
    blocks_by_source: Dict[str, List[BibBlock]] = {}
    global_key_to_label: Dict[str, str] = {}
    for source_path, source_rel in source_files:
        try:
            text = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"WARN: read failed {source_path}: {exc}")
            continue
        blocks = parse_bib_blocks(source_path, source_rel, text)
        blocks_by_source[source_rel] = blocks
        all_blocks.extend(blocks)
        for block in blocks:
            if block.cite_key:
                global_key_to_label[slugify(block.cite_key)] = block.label

    next_kg_id = parallel_kg_id_factory(datetime.now(timezone.utc))
    created = 0
    processed = 0

    for source_rel in sorted(blocks_by_source.keys()):
        blocks = blocks_by_source[source_rel]
        local_key_to_label = {
            slugify(block.cite_key): block.label for block in blocks if block.cite_key
        }
        for block in blocks:
            processed += 1
            if block.label in existing_labels:
                continue

            parents = choose_parent_labels(
                block,
                local_key_to_label=local_key_to_label,
                global_key_to_label=global_key_to_label,
                existing_key_to_label=existing_bib_key_to_label,
            )
            payload_bytes = block.payload_text.encode("utf-8")
            kg_id = next_kg_id()
            type_token = block.atom_type[3:] if block.atom_type.startswith("tp-") else block.atom_type
            filename = f"{kg_id}__lbl-{block.label}__tp-{type_token}__h-{block.payload_hash12}.bib"
            atom_path = atoms_dir / filename
            meta_path = atom_sidecar_path(atom_path)
            meta = {
                "kg_id": kg_id,
                "label": block.label,
                "atom_type": block.atom_type,
                "parents": parents,
                "parent_edges": [
                    {
                        "parent": parent,
                        "edge_type": "bib_crossref",
                        "edge_source": "kg_sync_bibliography_atoms",
                        "edge_reason": "crossref_field",
                    }
                    for parent in parents
                ],
                "edge_schema_version": "v2",
                "source_path": block.source_path.as_posix(),
                "source_rel_path": block.source_rel,
                "source_tex_label": "",
                "canonical_label": block.canonical_label,
                "task_id": "",
                "task_kind": "source_bibliography_block",
                "merged_sha256": "",
                "merged_tex_path": "",
                "merged_map_path": "",
                "unit_fingerprint": block.payload_hash12,
                "unit_env": block.entry_type or "bib",
                "extractor_version": SCRIPT_VERSION,
                "proof_orphan": False,
                "citation_key": block.cite_key,
                "bib_entry_type": block.entry_type,
                "source_name": spec.name,
                "raw_block": bool(not block.cite_key),
            }
            if args.dry_run:
                print(f"[DRY-RUN] create atom {atom_path}")
            else:
                atom_path.write_bytes(payload_bytes)
                write_json(meta_path, meta)
            existing_labels.add(block.label)
            label_to_payload[block.label] = block.payload_text
            created += 1
            if block.cite_key:
                existing_bib_key_to_label[slugify(block.cite_key)] = block.label

    output_dir = kg_root / "bibliography"
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = kg_root / ".kgcache" / "bibliography" / "sync_state.json"
    prev_state = read_json(state_path)
    prev_generated = [
        str(x)
        for x in (prev_state.get("generated_files") or [])
        if isinstance(x, str) and x.strip()
    ]

    generated_files: List[str] = []
    used_output_names: set[str] = set()
    written_files = 0
    for source_rel in sorted(blocks_by_source.keys()):
        blocks = blocks_by_source[source_rel]
        out_name = make_output_name(source_rel, used_output_names)
        out_path = output_dir / out_name
        chunks: List[str] = []
        for block in blocks:
            payload = label_to_payload.get(block.label, block.payload_text).strip()
            if not payload:
                continue
            chunks.append(payload)
        body = "\n\n".join(chunks).strip()
        content = (
            "% generated by kg_sync_bibliography_atoms.py\n"
            f"% source: {(spec.root / source_rel).resolve().as_posix()}\n\n"
            f"{body}\n"
            if body
            else "% generated by kg_sync_bibliography_atoms.py\n"
        )
        rel_output = out_path.relative_to(kg_root).as_posix()
        generated_files.append(rel_output)
        if args.dry_run:
            print(f"[DRY-RUN] write bibliography {out_path} ({len(chunks)} blocks)")
            continue
        old = ""
        if out_path.exists():
            try:
                old = out_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                old = ""
        if old != content:
            out_path.write_text(content, encoding="utf-8")
            written_files += 1

    removed_files = 0
    if not args.no_clean_output and not args.dry_run:
        keep = set(generated_files)
        for rel in prev_generated:
            if rel in keep:
                continue
            p = (kg_root / rel).resolve()
            if not p.exists() or p.is_dir():
                continue
            try:
                if p.suffix.lower() == ".bib" and output_dir in p.parents:
                    p.unlink()
                    removed_files += 1
            except OSError:
                continue

    state = {
        "timestamp": now_utc_compact(),
        "script_version": SCRIPT_VERSION,
        "source_spec": str(spec_path),
        "source_root": spec.root.as_posix(),
        "source_file_count": len(source_files),
        "parsed_block_count": processed,
        "created_atom_count": created,
        "generated_files": generated_files,
    }
    if not args.dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"source_files={len(source_files)} parsed_blocks={processed}")
    print(f"created_atoms={created}")
    print(
        f"bibliography_written={written_files} bibliography_removed={removed_files} "
        f"generated={len(generated_files)}"
    )
    print(f"state: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
