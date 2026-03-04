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

try:
    from pylatexenc.latexwalker import LatexMacroNode, LatexWalker
except ImportError:
    LatexMacroNode = None
    LatexWalker = None

# Legacy format (kept for backward compatibility):
#   <id>__lbl-<label>__tp-<type>__from-<parents>__h-<hash>.<ext>
ATOM_RE_LEGACY = re.compile(
    r"^(?P<id>KG-\d{8}-\d{4,})"
    r"__lbl-(?P<label>[a-z0-9-]+)"
    r"__tp-(?P<type>[a-z0-9-]+)"
    r"__from-(?P<parents>[a-z0-9-+]+)"
    r"__h-(?P<hash>[0-9a-f]{12})"
    r"\.(?P<ext>[A-Za-z0-9._-]+)$"
)

# Current format (relations stored in sidecar JSON):
#   <id>__lbl-<label>__tp-<type>__h-<hash>.<ext>
ATOM_RE = re.compile(
    r"^(?P<id>KG-\d{8}-\d{4,})"
    r"__lbl-(?P<label>[a-z0-9-]+)"
    r"__tp-(?P<type>[a-z0-9-]+)"
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


def compact_label(label: str, max_len: int = 56) -> str:
    """Keep labels filename-safe while preserving readable prefix."""
    label = slugify(label)
    if len(label) <= max_len:
        return label
    suffix = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
    head_len = max(8, max_len - 9)
    head = label[:head_len].rstrip("-")
    return f"{head}-{suffix}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
GENFRAG_LABEL_RE = re.compile(r"\\genfraglabel\{([^}]+)\}")
REF_RE = re.compile(
    r"\\(?:ref|eqref|autoref|cref|Cref|pageref|vref|nameref)\{([^}]+)\}"
)
CITE_RE = re.compile(r"\\(?:cite|citet|citep)\{([^}]+)\}")
REF_MACROS = {"ref", "eqref", "autoref", "cref", "Cref", "pageref", "vref", "nameref"}
LABEL_MACROS = {"label", "genfraglabel"}
CITE_MACROS = {"cite", "citet", "citep"}


def strip_tex_comments(text: str) -> str:
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw
        cut = None
        for idx, ch in enumerate(line):
            if ch != "%":
                continue
            if idx > 0 and line[idx - 1] == "\\":
                continue
            cut = idx
            break
        if cut is not None:
            line = line[:cut]
        lines.append(line)
    out = "\n".join(lines)
    if text.endswith("\n"):
        out += "\n"
    return out


def split_latex_csv(value: str) -> List[str]:
    out: List[str] = []
    for part in value.split(","):
        item = part.strip()
        if item:
            out.append(item)
    return out


def _macro_first_braced_arg_text(node) -> str:
    if LatexMacroNode is None or not isinstance(node, LatexMacroNode):
        return ""
    if not node.nodeargd or not node.nodeargd.argnlist:
        return ""
    for arg in node.nodeargd.argnlist:
        if arg is None or not hasattr(arg, "latex_verbatim"):
            continue
        raw = arg.latex_verbatim().strip()
        if raw.startswith("{") and raw.endswith("}"):
            return raw[1:-1].strip()
    return ""


def _iter_nodes_recursive(nodes):
    for node in nodes or []:
        yield node
        if hasattr(node, "nodelist") and node.nodelist:
            yield from _iter_nodes_recursive(node.nodelist)
        if LatexMacroNode is not None and isinstance(node, LatexMacroNode) and node.nodeargd:
            for arg in node.nodeargd.argnlist:
                if arg is not None and hasattr(arg, "nodelist") and arg.nodelist:
                    yield from _iter_nodes_recursive(arg.nodelist)


def _label_aliases(label: str) -> Set[str]:
    value = label.strip()
    out = {value}
    if ":" in value:
        out.add(value.replace(":", "__"))
    if "__" in value:
        out.add(value.replace("__", ":"))
    return {x for x in out if x}


def extract_tex_crossrefs(text: str) -> Tuple[Set[str], Set[str], Set[str]]:
    if LatexWalker is None:
        cleaned = strip_tex_comments(text)
        labels = set(LABEL_RE.findall(cleaned))
        labels.update(GENFRAG_LABEL_RE.findall(cleaned))
        refs: Set[str] = set()
        for raw in REF_RE.findall(cleaned):
            refs.update(split_latex_csv(raw))
        cites: Set[str] = set()
        for raw in CITE_RE.findall(cleaned):
            cites.update(split_latex_csv(raw))
        aliased_labels: Set[str] = set()
        for lb in labels:
            aliased_labels.update(_label_aliases(lb))
        return aliased_labels, refs, cites

    labels: Set[str] = set()
    refs: Set[str] = set()
    cites: Set[str] = set()
    try:
        nodes, _, _ = LatexWalker(text).get_latex_nodes(pos=0)
    except Exception:
        cleaned = strip_tex_comments(text)
        labels = set(LABEL_RE.findall(cleaned))
        labels.update(GENFRAG_LABEL_RE.findall(cleaned))
        refs = set()
        for raw in REF_RE.findall(cleaned):
            for ref in split_latex_csv(raw):
                refs.update(_label_aliases(ref))
        cites = set()
        for raw in CITE_RE.findall(cleaned):
            cites.update(split_latex_csv(raw))
        aliased_labels: Set[str] = set()
        for lb in labels:
            aliased_labels.update(_label_aliases(lb))
        return aliased_labels, refs, cites

    for node in _iter_nodes_recursive(nodes):
        if LatexMacroNode is None or not isinstance(node, LatexMacroNode):
            continue
        macro = node.macroname
        arg = _macro_first_braced_arg_text(node)
        if not arg:
            continue
        if macro in LABEL_MACROS:
            for label in split_latex_csv(arg):
                labels.update(_label_aliases(label))
        elif macro in REF_MACROS:
            refs.update(split_latex_csv(arg))
        elif macro in CITE_MACROS:
            cites.update(split_latex_csv(arg))

    # Some custom macros may be unknown to LatexWalker and keep raw braces in
    # char nodes. Merge a comment-stripped regex fallback for completeness.
    cleaned = strip_tex_comments(text)
    for raw in LABEL_RE.findall(cleaned):
        for label in split_latex_csv(raw):
            labels.update(_label_aliases(label))
    for raw in GENFRAG_LABEL_RE.findall(cleaned):
        for label in split_latex_csv(raw):
            labels.update(_label_aliases(label))
    for raw in REF_RE.findall(cleaned):
        refs.update(split_latex_csv(raw))
    for raw in CITE_RE.findall(cleaned):
        cites.update(split_latex_csv(raw))

    return labels, refs, cites


def tex_input_fragment_status(path: Path) -> Tuple[bool, Optional[str]]:
    """Return whether a TeX file is safe to include via \\input in a parent document."""
    if path.suffix.lower() != ".tex":
        return False, "not a .tex file"

    text = read_text(path)
    cleaned = strip_tex_comments(text)

    checks = (
        (r"\\documentclass\b", "contains \\documentclass"),
        (r"\\begin\s*\{\s*document\s*\}", "contains \\begin{document}"),
        (r"\\end\s*\{\s*document\s*\}", "contains \\end{document}"),
        (
            r"\\if(?:x|num|dim|odd|vmode|hmode|mmode|inner|cat|defined|csname|true|false|case|void|hbox|vbox|eof)?(?![A-Za-z@])",
            "contains TeX conditional control (\\if...)",
        ),
        (r"\\fi(?![A-Za-z@])", "contains TeX conditional control (\\fi)"),
        (r"\\makeatletter\b", "contains \\makeatletter"),
        (r"\\makeatother\b", "contains \\makeatother"),
        (r"\\ExplSyntaxOn\b", "contains \\ExplSyntaxOn"),
        (r"\\ExplSyntaxOff\b", "contains \\ExplSyntaxOff"),
        (r"\\catcode\b", "contains \\catcode"),
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
    if match:
        kg_id = match.group("id")
        label = match.group("label")
        atom_type = f"tp-{match.group('type')}"
        hash12 = match.group("hash")
        ext = match.group("ext")
        # New format stores parents in sidecar JSON.
        return kg_id, label, atom_type, tuple(), hash12, ext

    legacy = ATOM_RE_LEGACY.match(path.name)
    if legacy:
        kg_id = legacy.group("id")
        label = legacy.group("label")
        atom_type = f"tp-{legacy.group('type')}"
        raw_parents = legacy.group("parents")
        if raw_parents == "root":
            parents = tuple()
        else:
            parts = [x for x in raw_parents.split("+") if x]
            parents = tuple(parts)
        hash12 = legacy.group("hash")
        ext = legacy.group("ext")
        return kg_id, label, atom_type, parents, hash12, ext
    return None


def atom_sidecar_path(atom_payload_path: Path) -> Path:
    return atom_payload_path.with_name(atom_payload_path.name + ".meta.json")


def scan_atoms(kg_root: Path, verify_hash: bool = True) -> Tuple[List[Atom], List[str]]:
    atoms_dir = kg_root / "atoms"
    errors: List[str] = []
    atoms: List[Atom] = []

    if not atoms_dir.exists():
        return atoms, [f"atoms directory not found: {atoms_dir}"]

    for path in sorted(atoms_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(".meta.json"):
            continue
        parsed = parse_atom_filename(path)
        if parsed is None:
            errors.append(f"invalid atom filename: {path}")
            continue

        kg_id, label, atom_type, parents, hash12, ext = parsed
        is_new_format = ATOM_RE.match(path.name) is not None
        if is_new_format:
            sidecar = atom_sidecar_path(path)
            if sidecar.exists():
                try:
                    meta = json.loads(sidecar.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"invalid sidecar json for {path.name}: {exc}")
                    meta = {}
                meta_parents = meta.get("parents")
                if isinstance(meta_parents, list):
                    parents = tuple(slugify(str(x)) for x in meta_parents if str(x).strip())
                elif meta_parents is None:
                    parents = tuple()
                else:
                    errors.append(f"invalid parents in sidecar for {path.name}: expected list")
                    parents = tuple()
            else:
                errors.append(f"missing sidecar meta json for {path.name}: {sidecar.name}")

        if verify_hash:
            sha = compute_sha256(path)
            if sha[:12] != hash12:
                errors.append(
                    f"hash mismatch for {path.name}: filename={hash12} actual={sha[:12]}"
                )
        else:
            # Trust filename hash for fast scan paths (compile/index hot path).
            sha = hash12

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
            # label_anchor atoms intentionally preserve only original \label{...}
            # and may not carry kgid/kg-label markers.
            skip_marker_check = False
            sidecar = atom_sidecar_path(atom.path)
            if sidecar.exists():
                try:
                    meta = json.loads(sidecar.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    meta = {}
                if str(meta.get("unit_env") or "").strip() == "label_anchor":
                    skip_marker_check = True

            if not skip_marker_check:
                text = read_text(atom.path)
                wanted_old = f"\\label{{kg:{atom.label}}}"
                short = hashlib.sha256(atom.label.encode("utf-8")).hexdigest()[:12]
                wanted_short = f"\\label{{kgid:{short}}}"
                wanted_comment = f"% kg-label:{atom.label}"
                if wanted_old not in text and wanted_short not in text and wanted_comment not in text:
                    warnings.append(
                        f"tex atom missing canonical label marker ({wanted_old} or {wanted_short}): {atom.path}"
                    )

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
            m = re.match(rf"^{re.escape(prefix)}(?P<seq>\d+)", name)
            if m:
                max_seq = max(max_seq, int(m.group("seq")))
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
