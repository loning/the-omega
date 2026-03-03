#!/usr/bin/env python3
"""Build index view .tex files from index spec definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from _kg_common import (
    Atom,
    ancestor_closure,
    atom_sidecar_path,
    default_kg_root,
    extract_tex_crossrefs,
    normalize_type,
    parse_bool,
    parse_kv_spec,
    scan_atoms,
    tex_input_fragment_status,
    topological_order,
)

INPUT_OR_INCLUDE_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
SUBFIX_RE = re.compile(r"\\subfix\{([^}]+)\}")
BIB_CMD_RE = re.compile(r"\\bibliography(?![A-Za-z@])")
BEGIN_DOC_RE = re.compile(r"\\begin\s*\{\s*document\s*\}")
END_DOC_RE = re.compile(r"\\end\s*\{\s*document\s*\}")
DOCUMENTCLASS_RE = re.compile(r"\\documentclass\b")
UNESCAPED_DOUBLE_DOLLAR_RE = re.compile(r"(?<!\\)\$\$")
BUILD_INDEX_VERSION = "2026-03-04-r3"


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
    tokens = [x.strip().lower() for x in value.split(",") if x.strip()]
    if not tokens or "*" in tokens or "all" in tokens:
        return set()
    out: Set[str] = set()
    for item in tokens:
        full_type, _ = normalize_type(item)
        out.add(full_type)
    return out


def parse_int(value: str, default: int) -> int:
    try:
        return int(value.strip())
    except Exception:
        return default


def load_atom_meta(atom: Atom) -> Dict[str, object]:
    sidecar = atom_sidecar_path(atom.path)
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def source_path_for_atom(atom: Atom) -> Optional[Path]:
    meta = load_atom_meta(atom)
    raw = str(meta.get("source_path") or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser()
    if p.is_absolute():
        return p.resolve()
    return p.resolve()


def source_basename_for_atom(atom: Atom) -> str:
    src = source_path_for_atom(atom)
    if src is None:
        return ""
    if src.suffix.lower() != ".tex":
        return ""
    return src.name


def rewrite_bibliography_command(line: str, source_dir: Optional[Path]) -> str:
    m = BIB_CMD_RE.search(line)
    if not m:
        return line
    macro_pos = m.start()

    brace_start = line.find("{", m.end())
    if brace_start < 0:
        return line

    depth = 0
    brace_end = -1
    for idx in range(brace_start, len(line)):
        ch = line[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                brace_end = idx
                break

    if brace_end < 0:
        return line

    inner = line[brace_start + 1 : brace_end]
    raw_entries = [x.strip() for x in inner.split(",") if x.strip()]
    rewritten: List[str] = []
    for entry in raw_entries:
        text = SUBFIX_RE.sub(r"\1", entry).strip()
        if not text:
            continue
        p = Path(text)
        if not p.is_absolute() and source_dir is not None:
            p = (source_dir / p).resolve()
        else:
            p = p.resolve()
        if p.suffix.lower() == ".bib":
            p = p.with_suffix("")
        rewritten.append(p.as_posix())

    if not rewritten:
        return line

    new_cmd = "\\bibliography{" + ",".join(rewritten) + "}"
    return line[:macro_pos] + new_cmd + line[brace_end + 1 :]


def unwrap_document_body(text: str) -> str:
    begin = BEGIN_DOC_RE.search(text)
    end = END_DOC_RE.search(text)
    if begin and end and end.start() > begin.end():
        return text[begin.end() : end.start()]
    return text


def sanitize_non_fragment_tex(atom: Atom) -> Tuple[Optional[str], str]:
    source = source_path_for_atom(atom)
    source_dir = source.parent if source is not None else None
    raw = atom.path.read_text(encoding="utf-8", errors="replace")
    body = unwrap_document_body(raw)

    kept: List[str] = []
    dropped_inputs = 0
    for line in body.splitlines():
        if DOCUMENTCLASS_RE.search(line):
            continue
        if BEGIN_DOC_RE.search(line) or END_DOC_RE.search(line):
            continue
        if INPUT_OR_INCLUDE_RE.search(line):
            dropped_inputs += 1
            continue
        rewritten = rewrite_bibliography_command(line, source_dir)
        kept.append(rewritten)

    trimmed_lines = [ln.rstrip() for ln in kept]
    # Remove leading/trailing blank lines after sanitization.
    while trimmed_lines and not trimmed_lines[0].strip():
        trimmed_lines.pop(0)
    while trimmed_lines and not trimmed_lines[-1].strip():
        trimmed_lines.pop()

    if not trimmed_lines:
        if dropped_inputs > 0:
            return None, f"sanitized wrapper dropped {dropped_inputs} input/include lines; no body left"
        return None, "sanitized wrapper has empty body"

    out_lines = [
        f"% sanitized-wrapper from {atom.path.name}",
        f"% source-label: {atom.label}",
    ]
    out_lines.extend(trimmed_lines)
    out = "\n".join(out_lines) + "\n"
    reason = f"sanitized wrapper fragment; dropped_inputs={dropped_inputs}"
    return out, reason


def repair_unbalanced_display_math(tex: str) -> Tuple[str, Optional[str]]:
    total_dbl = len(UNESCAPED_DOUBLE_DOLLAR_RE.findall(tex))
    if total_dbl % 2 == 0:
        return tex, None

    lines = tex.splitlines()
    repaired_lines: List[str] = []
    in_display = False
    changed = False

    for line in lines:
        if in_display and not line.strip():
            repaired_lines.append("$$")
            in_display = False
            changed = True

        repaired_lines.append(line)

        toggles = len(UNESCAPED_DOUBLE_DOLLAR_RE.findall(line))
        if toggles % 2 == 1:
            in_display = not in_display

    if in_display:
        if repaired_lines and re.match(r"^\s*\\end\{[A-Za-z*@]+\}\s*$", repaired_lines[-1]):
            repaired_lines.insert(len(repaired_lines) - 1, "$$")
        else:
            repaired_lines.append("$$")
        changed = True

    if not changed:
        # Safety fallback: append closing $$ at end.
        repaired_lines.append("$$")
        changed = True

    repaired = "\n".join(repaired_lines)
    if tex.endswith("\n"):
        repaired += "\n"
    return repaired, "repaired odd unescaped $$ pair by inserting closing $$"


def collect_tex_crossref_index(
    tex_atoms: Sequence[Atom],
) -> Tuple[Dict[str, Dict[str, Set[str]]], Dict[str, str], List[str]]:
    """Return per-atom label/ref/cite sets and reverse label->atom map."""
    per_atom: Dict[str, Dict[str, Set[str]]] = {}
    label_to_atom: Dict[str, str] = {}
    label_to_atom_kgid: Dict[str, str] = {}
    errors: List[str] = []

    for atom in tex_atoms:
        try:
            text = atom.path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"read failed for {atom.path}: {exc}")
            per_atom[atom.label] = {"labels": set(), "refs": set(), "cites": set()}
            continue

        labels, refs, cites = extract_tex_crossrefs(text)
        per_atom[atom.label] = {"labels": labels, "refs": refs, "cites": cites}

        for source_label in labels:
            existing_kgid = label_to_atom_kgid.get(source_label)
            if existing_kgid is None:
                label_to_atom[source_label] = atom.label
                label_to_atom_kgid[source_label] = atom.kg_id
                continue
            # Prefer newest atom if multiple atoms define same source label.
            if atom.kg_id > existing_kgid:
                label_to_atom[source_label] = atom.label
                label_to_atom_kgid[source_label] = atom.kg_id

    return per_atom, label_to_atom, errors


def selection_ref_sets(
    selected_labels: Set[str],
    by_label: Dict[str, Atom],
    tex_ref_index: Dict[str, Dict[str, Set[str]]],
) -> Tuple[Set[str], Set[str], Set[str]]:
    defined_labels: Set[str] = set()
    refs: Set[str] = set()
    cites: Set[str] = set()
    for label in selected_labels:
        atom = by_label.get(label)
        if atom is None or atom.ext != "tex":
            continue
        rec = tex_ref_index.get(label)
        if not rec:
            continue
        defined_labels.update(rec.get("labels", set()))
        refs.update(rec.get("refs", set()))
        cites.update(rec.get("cites", set()))
    return defined_labels, refs, cites


def apply_reference_closure(
    selected_labels: Set[str],
    by_label: Dict[str, Atom],
    tex_ref_index: Dict[str, Dict[str, Set[str]]],
    source_label_to_atom: Dict[str, str],
    max_rounds: int,
) -> Tuple[Set[str], Dict[str, object]]:
    selected = set(selected_labels)
    added_labels: Set[str] = set()
    rounds: List[Dict[str, object]] = []

    for ridx in range(1, max_rounds + 1):
        defined_labels, refs, _ = selection_ref_sets(selected, by_label, tex_ref_index)
        missing_refs = sorted(refs - defined_labels)

        seed_atoms: Set[str] = set()
        unresolved: List[str] = []
        for ref in missing_refs:
            target = source_label_to_atom.get(ref)
            if target:
                if target not in selected:
                    seed_atoms.add(target)
            else:
                unresolved.append(ref)

        if not seed_atoms:
            rounds.append(
                {
                    "round": ridx,
                    "missing_refs": len(missing_refs),
                    "added_seed_atoms": 0,
                    "added_total_atoms": 0,
                }
            )
            break

        expanded = ancestor_closure(seed_atoms, by_label)
        new_atoms = expanded - selected
        rounds.append(
            {
                "round": ridx,
                "missing_refs": len(missing_refs),
                "added_seed_atoms": len(seed_atoms),
                "added_total_atoms": len(new_atoms),
            }
        )

        if not new_atoms:
            break

        selected.update(new_atoms)
        added_labels.update(new_atoms)

    final_defined, final_refs, final_cites = selection_ref_sets(selected, by_label, tex_ref_index)
    final_missing = sorted(final_refs - final_defined)

    report: Dict[str, object] = {
        "closure_enabled": True,
        "max_rounds": max_rounds,
        "rounds": rounds,
        "added_atom_labels": sorted(added_labels),
        "added_atom_count": len(added_labels),
        "final_defined_label_count": len(final_defined),
        "final_unique_ref_count": len(final_refs),
        "final_missing_ref_count": len(final_missing),
        "final_missing_refs": final_missing,
        "final_unique_cite_count": len(final_cites),
    }
    return selected, report


def selection_fingerprint(
    *,
    spec_path: Path,
    roots: List[str],
    include_types: Set[str],
    order: str,
    auto_include_methods: bool,
    reference_closure: bool,
    closure_max_rounds: int,
    include_wrapper_fragments: bool,
    expose_source_aliases: bool,
    ordered_atoms: Sequence[Atom],
    includable_entries: Sequence[Tuple[Atom, str]],
    skipped_tex_atoms: Sequence[Tuple[Atom, str]],
    closure_report: Dict[str, object],
    source_aliases: Dict[str, str],
) -> str:
    hasher = hashlib.sha256()
    hasher.update(spec_path.resolve().as_posix().encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(BUILD_INDEX_VERSION.encode("utf-8"))
    hasher.update(b"\n")
    hasher.update(
        json.dumps(
            {
                "roots": sorted(roots),
                "include_types": sorted(include_types),
                "order": order,
                "auto_include_methods": bool(auto_include_methods),
                "reference_closure": bool(reference_closure),
                "closure_max_rounds": int(closure_max_rounds),
                "include_wrapper_fragments": bool(include_wrapper_fragments),
                "expose_source_aliases": bool(expose_source_aliases),
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    )
    hasher.update(b"\n")

    for atom in ordered_atoms:
        hasher.update(
            f"{atom.kg_id}|{atom.label}|{atom.atom_type}|{atom.ext}|{atom.hash12}\n".encode("utf-8")
        )

    hasher.update(b"#includable\n")
    for atom, mode in includable_entries:
        hasher.update(f"{atom.kg_id}|{mode}\n".encode("utf-8"))

    hasher.update(b"#skipped\n")
    for atom, reason in skipped_tex_atoms:
        hasher.update(f"{atom.kg_id}|{reason}\n".encode("utf-8"))

    hasher.update(b"#source_aliases\n")
    for alias, atom_label in sorted(source_aliases.items()):
        hasher.update(f"{alias}|{atom_label}\n".encode("utf-8"))

    hasher.update(b"#closure_report\n")
    hasher.update(json.dumps(closure_report, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    hasher.update(b"\n")

    return hasher.hexdigest()


def build_single_spec(kg_root: Path, spec_path: Path) -> Path:
    data = parse_kv_spec(spec_path)
    name = data.get("name", spec_path.stem)
    roots = parse_roots(data.get("roots", ""))
    include_types = parse_types(data.get("include_types", ""))
    order = data.get("order", "topo").strip().lower()
    auto_include_methods = parse_bool(data.get("auto_include_methods", "false"), default=False)
    reference_closure = parse_bool(data.get("reference_closure", "true"), default=True)
    closure_max_rounds = max(1, min(parse_int(data.get("reference_closure_max_rounds", "12"), 12), 64))
    include_wrapper_fragments = parse_bool(data.get("include_wrapper_fragments", "true"), default=True)
    expose_source_aliases = parse_bool(data.get("expose_source_aliases", "true"), default=True)

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

    selected_labels = {a.label for a in selected_atoms}

    tex_atoms = [a for a in atoms if a.ext == "tex"]
    tex_ref_index, source_label_to_atom, parse_errors = collect_tex_crossref_index(tex_atoms)

    if reference_closure:
        selected_labels, closure_report = apply_reference_closure(
            selected_labels,
            by_label,
            tex_ref_index,
            source_label_to_atom,
            closure_max_rounds,
        )
    else:
        final_defined, final_refs, final_cites = selection_ref_sets(selected_labels, by_label, tex_ref_index)
        final_missing = sorted(final_refs - final_defined)
        closure_report = {
            "closure_enabled": False,
            "max_rounds": 0,
            "rounds": [],
            "added_atom_labels": [],
            "added_atom_count": 0,
            "final_defined_label_count": len(final_defined),
            "final_unique_ref_count": len(final_refs),
            "final_missing_ref_count": len(final_missing),
            "final_missing_refs": final_missing,
            "final_unique_cite_count": len(final_cites),
        }

    selected_atoms = [a for a in atoms if a.label in selected_labels]

    if order == "topo":
        ordered = topological_order(atoms, subset={a.label for a in selected_atoms})
    elif order == "alpha":
        ordered = sorted(selected_atoms, key=lambda a: a.label)
    else:
        raise ValueError(f"unsupported order {order} in {spec_path}")

    tex_atoms_ordered = [a for a in ordered if a.ext == "tex"]
    non_tex_atoms = [a for a in ordered if a.ext != "tex"]

    includable_entries: List[Tuple[Atom, str]] = []
    sanitized_payloads: Dict[str, str] = {}
    skipped_tex_atoms: List[Tuple[Atom, str]] = []

    for atom in tex_atoms_ordered:
        ok, reason = tex_input_fragment_status(atom.path)
        if ok:
            raw = atom.path.read_text(encoding="utf-8", errors="replace")
            repaired, repair_reason = repair_unbalanced_display_math(raw)
            if repair_reason is None:
                includable_entries.append((atom, "original"))
            else:
                includable_entries.append((atom, "repaired"))
                sanitized_payloads[atom.label] = repaired
            continue

        if not include_wrapper_fragments:
            skipped_tex_atoms.append((atom, reason or "not input-fragment safe"))
            continue

        payload, sanitize_reason = sanitize_non_fragment_tex(atom)
        if payload is None:
            skipped_tex_atoms.append((atom, sanitize_reason))
            continue

        repaired, repair_reason = repair_unbalanced_display_math(payload)
        if repair_reason:
            sanitize_reason = f"{sanitize_reason}; {repair_reason}"
        includable_entries.append((atom, "sanitized"))
        sanitized_payloads[atom.label] = repaired

    includable_tex_atoms = [atom for atom, _ in includable_entries]

    # Build additional basename aliases for wrapper-level \input{foo}.
    source_basename_to_labels: Dict[str, List[str]] = defaultdict(list)
    if expose_source_aliases:
        for atom in includable_tex_atoms:
            base = source_basename_for_atom(atom)
            if base:
                source_basename_to_labels[base].append(atom.label)

    source_aliases: Dict[str, str] = {}
    for base, labels in source_basename_to_labels.items():
        uniq = sorted(set(labels))
        if len(uniq) == 1:
            source_aliases[base] = uniq[0]

    out_dir = kg_root / "index_nodes" / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tex = out_dir / f"idx_{name}_main.tex"
    alias_dir = out_dir / "atoms"
    manifest_path = out_dir / "manifest.json"
    closure_report_path = out_dir / "reference_closure_report.json"

    if parse_errors:
        closure_report["tex_parse_errors"] = parse_errors

    fingerprint = selection_fingerprint(
        spec_path=spec_path,
        roots=roots,
        include_types=include_types,
        order=order,
        auto_include_methods=auto_include_methods,
        reference_closure=reference_closure,
        closure_max_rounds=closure_max_rounds,
        include_wrapper_fragments=include_wrapper_fragments,
        expose_source_aliases=expose_source_aliases,
        ordered_atoms=ordered,
        includable_entries=includable_entries,
        skipped_tex_atoms=skipped_tex_atoms,
        closure_report=closure_report,
        source_aliases=source_aliases,
    )
    if manifest_path.exists() and out_tex.exists() and alias_dir.exists() and closure_report_path.exists():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_manifest = {}
        if previous_manifest.get("selection_fingerprint") == fingerprint:
            expected_aliases = [alias_dir / f"{atom.kg_id}.tex" for atom in includable_tex_atoms]
            if all(p.exists() for p in expected_aliases):
                return out_tex

    if alias_dir.exists():
        shutil.rmtree(alias_dir)
    alias_dir.mkdir(parents=True, exist_ok=True)

    atom_to_alias_name: Dict[str, str] = {}

    lines: List[str] = []
    lines.append("% Auto-generated by kg_build_index.py")
    lines.append(f"% spec: {spec_path}")
    lines.append(f"\\section*{{Index: {latex_escape(name)}}}")
    lines.append("\\subsection*{Included TeX Atoms}")

    if includable_entries:
        for atom, mode in includable_entries:
            alias_name = f"{atom.kg_id}.tex"
            atom_to_alias_name[atom.label] = alias_name
            alias_path = alias_dir / alias_name

            if mode == "original":
                src_path = atom.path.resolve()
                try:
                    alias_path.symlink_to(src_path)
                except OSError:
                    shutil.copy2(src_path, alias_path)
            else:
                alias_path.write_text(sanitized_payloads[atom.label], encoding="utf-8")

            tex_path = (Path("atoms") / alias_name).as_posix()
            lines.append(f"% {atom.kg_id} {atom.label} {atom.atom_type} mode={mode}")
            lines.append(f"\\kginput{{{tex_path}}}")

        for source_alias, atom_label in sorted(source_aliases.items()):
            target_alias = atom_to_alias_name.get(atom_label)
            if not target_alias:
                continue
            alias_path = alias_dir / source_alias
            if alias_path.exists():
                continue
            try:
                alias_path.symlink_to(target_alias)
            except OSError:
                shutil.copy2(alias_dir / target_alias, alias_path)
    else:
        lines.append("\\emph{No TeX atoms selected.}")

    lines.append("\\subsection*{Skipped TeX Atoms}")
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

    lines.append("\\subsection*{Reference Closure Summary}")
    lines.append("\\begin{itemize}")
    lines.append(
        "\\item "
        f"closure enabled=\\texttt{{{str(bool(reference_closure)).lower()}}}, "
        f"added atoms=\\texttt{{{closure_report.get('added_atom_count', 0)}}}"
    )
    lines.append(
        "\\item "
        f"defined labels=\\texttt{{{closure_report.get('final_defined_label_count', 0)}}}, "
        f"unique refs=\\texttt{{{closure_report.get('final_unique_ref_count', 0)}}}, "
        f"missing refs=\\texttt{{{closure_report.get('final_missing_ref_count', 0)}}}"
    )
    lines.append("\\end{itemize}")

    out_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")

    closure_report_path.write_text(
        json.dumps(closure_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ambiguous_alias_count = sum(1 for labels in source_basename_to_labels.values() if len(set(labels)) > 1)

    manifest = {
        "name": name,
        "spec": str(spec_path),
        "roots": roots,
        "include_types": sorted(include_types),
        "order": order,
        "auto_include_methods": bool(auto_include_methods),
        "reference_closure": bool(reference_closure),
        "reference_closure_max_rounds": closure_max_rounds,
        "include_wrapper_fragments": bool(include_wrapper_fragments),
        "expose_source_aliases": bool(expose_source_aliases),
        "selection_fingerprint": fingerprint,
        "atom_count": len(ordered),
        "tex_atom_count": len(tex_atoms_ordered),
        "includable_tex_atom_count": len(includable_tex_atoms),
        "sanitized_tex_atom_count": sum(1 for _, mode in includable_entries if mode == "sanitized"),
        "repaired_tex_atom_count": sum(1 for _, mode in includable_entries if mode == "repaired"),
        "skipped_tex_atom_count": len(skipped_tex_atoms),
        "non_tex_atom_count": len(non_tex_atoms),
        "source_alias_count": len(source_aliases),
        "source_alias_ambiguous_count": ambiguous_alias_count,
        "reference_closure_report": str(closure_report_path),
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
