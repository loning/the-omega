#!/usr/bin/env python3
"""Shared utilities for knowledgegraph scripts."""

from __future__ import annotations

import hashlib
import json
import re
from fnmatch import fnmatchcase
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

ATOM_RE = re.compile(
    r"^(?P<id>KG-\d{8}-\d{4})"
    r"__lbl-(?P<label>[a-z0-9-]+)"
    r"__tp-(?P<type>[a-z0-9-]+)"
    r"__from-(?P<parents>[a-z0-9-+]+)"
    r"__h-(?P<hash>[0-9a-f]{12})"
    r"\.(?P<ext>[A-Za-z0-9._-]+)$"
)


@dataclass(frozen=True)
class Atom:
    kg_id: str
    label: str
    atom_type: str
    parents: Tuple[str, ...]
    hash12: str
    ext: str
    path: Path
    sha256: str

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["path"] = str(self.path)
        data["parents"] = list(self.parents)
        return data


@dataclass(frozen=True)
class SourceSpec:
    name: str
    root: Path
    include: Tuple[str, ...]
    exclude: Tuple[str, ...]
    hash_name: str
    spec_path: Path


def default_kg_root(script_file: str) -> Path:
    return Path(script_file).resolve().parent.parent


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_type(raw_type: str) -> Tuple[str, str]:
    token = raw_type[3:] if raw_type.startswith("tp-") else raw_type
    token = token.strip().lower()
    if not token:
        token = "claim"
    return f"tp-{token}", token


def slugify(text: str) -> str:
    lowered = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "atom"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tex_input_fragment_status(path: Path) -> Tuple[bool, Optional[str]]:
    """Return whether a TeX file is safe to include via \\input in a parent document."""
    if path.suffix.lower() != ".tex":
        return False, "not a .tex file"

    text = read_text(path)
    cleaned_lines = []
    for line in text.splitlines():
        # Ignore comments to avoid false positives from documentation text.
        cleaned_lines.append(line.split("%", 1)[0])
    cleaned = "\n".join(cleaned_lines)

    checks = (
        (r"\\documentclass\b", "contains \\documentclass"),
        (r"\\begin\s*\{\s*document\s*\}", "contains \\begin{document}"),
        (r"\\end\s*\{\s*document\s*\}", "contains \\end{document}"),
    )
    for pattern, reason in checks:
        if re.search(pattern, cleaned):
            return False, reason
    return True, None


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash12_for_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def parse_atom_filename(path: Path) -> Optional[Tuple[str, str, str, Tuple[str, ...], str, str]]:
    match = ATOM_RE.match(path.name)
    if not match:
        return None
    kg_id = match.group("id")
    label = match.group("label")
    atom_type = f"tp-{match.group('type')}"
    raw_parents = match.group("parents")
    parents: Tuple[str, ...]
    if raw_parents == "root":
        parents = tuple()
    else:
        parts = [x for x in raw_parents.split("+") if x]
        parents = tuple(parts)
    hash12 = match.group("hash")
    ext = match.group("ext")
    return kg_id, label, atom_type, parents, hash12, ext


def scan_atoms(kg_root: Path) -> Tuple[List[Atom], List[str]]:
    atoms_dir = kg_root / "atoms"
    errors: List[str] = []
    atoms: List[Atom] = []

    if not atoms_dir.exists():
        return atoms, [f"atoms directory not found: {atoms_dir}"]

    for path in sorted(atoms_dir.rglob("*")):
        if not path.is_file():
            continue
        parsed = parse_atom_filename(path)
        if parsed is None:
            errors.append(f"invalid atom filename: {path}")
            continue

        kg_id, label, atom_type, parents, hash12, ext = parsed
        sha = compute_sha256(path)
        if sha[:12] != hash12:
            errors.append(
                f"hash mismatch for {path.name}: filename={hash12} actual={sha[:12]}"
            )

        atoms.append(
            Atom(
                kg_id=kg_id,
                label=label,
                atom_type=atom_type,
                parents=parents,
                hash12=hash12,
                ext=ext,
                path=path,
                sha256=sha,
            )
        )

    return atoms, errors


def build_atom_maps(atoms: Sequence[Atom]) -> Tuple[Dict[str, Atom], Dict[str, Atom]]:
    by_id: Dict[str, Atom] = {}
    by_label: Dict[str, Atom] = {}
    for atom in atoms:
        by_id[atom.kg_id] = atom
        by_label[atom.label] = atom
    return by_id, by_label


def detect_cycles(labels: Iterable[str], parents_by_label: Dict[str, Tuple[str, ...]]) -> List[List[str]]:
    state: Dict[str, int] = {}
    stack: List[str] = []
    cycles: List[List[str]] = []

    def dfs(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for parent in parents_by_label.get(node, tuple()):
            if parent not in parents_by_label:
                continue
            pstate = state.get(parent, 0)
            if pstate == 0:
                dfs(parent)
            elif pstate == 1:
                if parent in stack:
                    idx = stack.index(parent)
                    cycles.append(stack[idx:] + [parent])
        stack.pop()
        state[node] = 2

    for label in labels:
        if state.get(label, 0) == 0:
            dfs(label)
    return cycles


def validate_atoms(atoms: Sequence[Atom]) -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    id_seen: Dict[str, Atom] = {}
    label_seen: Dict[str, Atom] = {}
    for atom in atoms:
        prev_id = id_seen.get(atom.kg_id)
        if prev_id is not None:
            errors.append(f"duplicate KG id: {atom.kg_id} ({prev_id.path}, {atom.path})")
        else:
            id_seen[atom.kg_id] = atom

        prev_label = label_seen.get(atom.label)
        if prev_label is not None:
            errors.append(
                f"duplicate label: {atom.label} ({prev_label.path}, {atom.path})"
            )
        else:
            label_seen[atom.label] = atom

        if atom.ext == "tex":
            text = read_text(atom.path)
            wanted = f"\\label{{kg:{atom.label}}}"
            if wanted not in text:
                warnings.append(f"tex atom missing canonical label {wanted}: {atom.path}")

    valid_labels = set(label_seen.keys())
    for atom in atoms:
        for parent in atom.parents:
            if parent not in valid_labels:
                errors.append(f"missing parent label: {parent} (child={atom.label})")

    parents_by_label = {a.label: a.parents for a in atoms}
    cycles = detect_cycles(valid_labels, parents_by_label)
    for cycle in cycles:
        errors.append(f"cycle detected: {' -> '.join(cycle)}")

    return {"errors": errors, "warnings": warnings}


def ancestor_closure(target_labels: Iterable[str], atoms_by_label: Dict[str, Atom]) -> Set[str]:
    selected: Set[str] = set()
    stack = list(target_labels)
    while stack:
        label = stack.pop()
        if label in selected:
            continue
        atom = atoms_by_label.get(label)
        if atom is None:
            continue
        selected.add(label)
        stack.extend(atom.parents)
    return selected


def topological_order(atoms: Sequence[Atom], subset: Optional[Set[str]] = None) -> List[Atom]:
    atoms_by_label = {a.label: a for a in atoms}
    selected_labels = set(atoms_by_label.keys()) if subset is None else set(subset)

    indegree: Dict[str, int] = {label: 0 for label in selected_labels}
    children: Dict[str, List[str]] = {label: [] for label in selected_labels}

    for label in selected_labels:
        atom = atoms_by_label[label]
        deps = [p for p in atom.parents if p in selected_labels]
        indegree[label] = len(deps)
        for p in deps:
            children.setdefault(p, []).append(label)

    queue = sorted([lbl for lbl, deg in indegree.items() if deg == 0])
    ordered: List[str] = []

    while queue:
        node = queue.pop(0)
        ordered.append(node)
        for child in sorted(children.get(node, [])):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
        queue.sort()

    if len(ordered) != len(selected_labels):
        raise ValueError("topological ordering failed due to cycle or missing node")

    return [atoms_by_label[label] for label in ordered]


def next_kg_id(kg_root: Path, now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    prefix = f"KG-{date_part}-"
    atoms_dir = kg_root / "atoms"
    max_seq = 0
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
    return f"{prefix}{max_seq + 1:04d}"


def parse_kv_spec(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def split_csv(value: str) -> Tuple[str, ...]:
    if not value:
        return tuple()
    return tuple(x.strip() for x in value.split(",") if x.strip())


def path_matches(path_rel_posix: str, patterns: Sequence[str]) -> bool:
    if not patterns:
        return True
    p = PurePosixPath(path_rel_posix)
    return any(p.match(pat) or fnmatchcase(path_rel_posix, pat) for pat in patterns)


def load_source_spec(spec_path: Path, kg_root: Path) -> SourceSpec:
    data = parse_kv_spec(spec_path)
    name = data.get("name") or spec_path.stem
    root_str = data.get("root")
    if not root_str:
        raise ValueError(f"missing root in source spec: {spec_path}")
    root = Path(root_str)
    if not root.is_absolute():
        # Prefer path relative to knowledgegraph root. If missing, fall back to repo root.
        primary = (kg_root / root).resolve()
        fallback = (kg_root.parent / root).resolve()
        root = primary if primary.exists() else fallback

    include = split_csv(data.get("include", "**/*"))
    exclude = split_csv(data.get("exclude", ""))
    hash_name = data.get("hash", "sha256").lower()
    if hash_name != "sha256":
        raise ValueError(f"unsupported hash algorithm {hash_name} in {spec_path}")

    return SourceSpec(
        name=name,
        root=root,
        include=include,
        exclude=exclude,
        hash_name=hash_name,
        spec_path=spec_path,
    )
