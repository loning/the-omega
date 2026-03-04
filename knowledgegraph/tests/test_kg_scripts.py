#!/usr/bin/env python3
"""Unit tests for knowledgegraph scripts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import _kg_common as common  # noqa: E402
import kg_build_index as build_index  # noqa: E402
import kg_compile as kg_compile  # noqa: E402
import kg_emit_llm_tasks as emit_tasks  # noqa: E402
import kg_ingest_atoms as ingest_atoms  # noqa: E402
import kg_latexpand_merge as latexpand_merge  # noqa: E402
import kg_watch_sources as watch_sources  # noqa: E402

HAS_PYLATEXENC = importlib.util.find_spec("pylatexenc") is not None


def _sha12(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def write_atom(
    kg_root: Path,
    *,
    kg_id: str,
    label: str,
    atom_type: str,
    parents: tuple[str, ...] = tuple(),
    ext: str = "tex",
    content: str | bytes | None = None,
) -> Path:
    atoms_dir = kg_root / "atoms"
    atoms_dir.mkdir(parents=True, exist_ok=True)

    if content is None:
        if ext == "tex":
            content = f"\\paragraph{{{label}}}\\label{{kg:{label}}}\n"
        else:
            content = f"{label}\n"

    payload = content.encode("utf-8") if isinstance(content, str) else content
    from_field = "+".join(parents) if parents else "root"
    type_token = atom_type[3:] if atom_type.startswith("tp-") else atom_type
    hash12 = _sha12(payload)
    name = (
        f"{kg_id}__lbl-{label}__tp-{type_token}__from-{from_field}"
        f"__h-{hash12}.{ext}"
    )
    path = atoms_dir / name
    path.write_bytes(payload)
    return path


class KGScriptsUnitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp.name)
        self.kg_root = self.repo_root / "knowledgegraph"
        (self.kg_root / "atoms").mkdir(parents=True, exist_ok=True)
        (self.kg_root / "index_specs").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_scan_validate_and_topological_order(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="base",
            atom_type="tp-def",
            parents=tuple(),
            ext="tex",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="theorem",
            atom_type="tp-thm",
            parents=("base",),
            ext="tex",
        )

        atoms, scan_errors = common.scan_atoms(self.kg_root)
        self.assertEqual(scan_errors, [])
        validation = common.validate_atoms(atoms)
        self.assertEqual(validation["errors"], [])

        ordered = common.topological_order(atoms)
        self.assertEqual([a.label for a in ordered], ["base", "theorem"])

    def test_cycle_detection(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="a",
            atom_type="tp-claim",
            parents=("b",),
            ext="txt",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="b",
            atom_type="tp-claim",
            parents=("a",),
            ext="txt",
        )

        atoms, scan_errors = common.scan_atoms(self.kg_root)
        self.assertEqual(scan_errors, [])
        validation = common.validate_atoms(atoms)
        self.assertTrue(any("cycle detected" in x for x in validation["errors"]))

    def test_scan_atoms_fast_mode_skips_hash_check(self) -> None:
        atoms_dir = self.kg_root / "atoms"
        atoms_dir.mkdir(parents=True, exist_ok=True)
        bad = atoms_dir / "KG-20260303-0001__lbl-a__tp-claim__from-root__h-000000000000.tex"
        bad.write_text("\\paragraph{a}\n", encoding="utf-8")

        _, errors_strict = common.scan_atoms(self.kg_root, verify_hash=True)
        self.assertTrue(any("hash mismatch" in e for e in errors_strict))

        _, errors_fast = common.scan_atoms(self.kg_root, verify_hash=False)
        self.assertFalse(any("hash mismatch" in e for e in errors_fast))

    def test_load_source_spec_fallback_to_repo_root(self) -> None:
        docs_dir = self.repo_root / "docs" / "papers"
        docs_dir.mkdir(parents=True, exist_ok=True)
        spec_path = self.kg_root / "source_specs.src"
        spec_path.write_text(
            "\n".join(
                [
                    "name: testsrc",
                    "root: docs/papers",
                    "include: *.tex,**/*.tex",
                    "hash: sha256",
                ]
            ),
            encoding="utf-8",
        )

        spec = common.load_source_spec(spec_path, self.kg_root)
        self.assertEqual(spec.name, "testsrc")
        self.assertEqual(spec.root, docs_dir.resolve())

    def test_watch_source_helpers_detect_rename(self) -> None:
        src = self.repo_root / "source"
        src.mkdir(parents=True, exist_ok=True)
        old = src / "old.txt"
        old.write_text("same\n", encoding="utf-8")

        snap1 = watch_sources.build_snapshot(src, ("*.txt", "**/*.txt"), tuple())
        self.assertIn("old.txt", snap1)

        new = src / "new.txt"
        old.rename(new)
        snap2 = watch_sources.build_snapshot(src, ("*.txt", "**/*.txt"), tuple())

        added = {p: h for p, h in snap2.items() if p not in snap1}
        deleted = {p: h for p, h in snap1.items() if p not in snap2}
        renames = watch_sources.detect_renames(added, deleted)
        self.assertEqual(len(renames), 1)
        self.assertEqual(renames[0][0], "old.txt")
        self.assertEqual(renames[0][1], "new.txt")

    def test_emit_tex_ast_helpers(self) -> None:
        if HAS_PYLATEXENC:
            tex = (
                "\\begin{lemma}\\label{lem:base}Base.\\end{lemma}\n"
                "\\begin{theorem}\\label{thm:main}By \\ref{lem:base}.\\end{theorem}\n"
                "\\begin{proof}Done.\\end{proof}\n"
            )
            units = emit_tasks.extract_tex_knowledge_units(tex, "sample")
            self.assertEqual(len(units), 3)
            self.assertEqual(units[0]["env"], "lemma")
            self.assertEqual(units[0]["source_label"], "lem:base")
            self.assertEqual(units[1]["env"], "theorem")
            self.assertEqual(units[1]["source_refs"], ["lem:base"])
            self.assertEqual(units[2]["env"], "proof")
            self.assertEqual(units[2]["source_refs"], ["thm:main"])
        else:
            with self.assertRaises(RuntimeError):
                emit_tasks.extract_tex_knowledge_units("\\begin{theorem}x\\end{theorem}", "sample")

    def test_emit_skips_nested_target_env_and_keeps_outer_label(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        tex = (
            "\\begin{theorem}\\label{thm:outer}\n"
            "Outer\n"
            "\\begin{equation}\\label{eq:inner}a=b\\end{equation}\n"
            "\\end{theorem}\n"
            "\\begin{equation}\\label{eq:standalone}c=d\\end{equation}\n"
        )
        units = emit_tasks.extract_tex_knowledge_units(tex, "sample")
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0]["env"], "theorem")
        self.assertEqual(units[0]["source_label"], "thm:outer")
        self.assertEqual(units[1]["env"], "equation")
        self.assertEqual(units[1]["source_label"], "eq:standalone")

    def test_emit_bundle_parser_extracts_units_by_source_file(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        tex_dir = self.repo_root / "src"
        tex_dir.mkdir(parents=True, exist_ok=True)
        f1 = tex_dir / "a.tex"
        f2 = tex_dir / "b.tex"
        f1.write_text(
            "\\begin{lemma}\\label{lem:a}A.\\end{lemma}\n"
            "\\begin{theorem}\\label{thm:a}By \\ref{lem:a}.\\end{theorem}\n",
            encoding="utf-8",
        )
        f2.write_text(
            "\\begin{definition}\\label{def:b}B.\\end{definition}\n",
            encoding="utf-8",
        )

        records = [
            {"change_type": "modified", "path": str(f1)},
            {"change_type": "modified", "path": str(f2)},
        ]
        bundle_tex, bundle_entries = emit_tasks.build_tex_bundle([f1, f2])
        units_index = emit_tasks.build_units_index_from_bundle(bundle_tex, bundle_entries)
        changed_paths = {
            Path(str(r["path"])).resolve().as_posix()
            for r in records
        }
        units_by_path = {p: units_index[p] for p in changed_paths if p in units_index}
        self.assertIn(f1.resolve().as_posix(), units_by_path)
        self.assertIn(f2.resolve().as_posix(), units_by_path)
        self.assertEqual(len(units_by_path[f1.resolve().as_posix()]), 2)
        self.assertEqual(len(units_by_path[f2.resolve().as_posix()]), 1)

    def test_emit_bundle_adds_label_anchor_for_labels_outside_target_env(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        tex_dir = self.repo_root / "src_anchor"
        tex_dir.mkdir(parents=True, exist_ok=True)
        f1 = tex_dir / "a.tex"
        f1.write_text(
            "\\section{S}\\label{sec:outside}\n"
            "\\begin{theorem}\\label{thm:in}\n"
            "\\begin{equation}\\label{eq:nested}a=b\\end{equation}\n"
            "\\end{theorem}\n",
            encoding="utf-8",
        )

        bundle_tex, bundle_entries = emit_tasks.build_tex_bundle([f1])
        units_index = emit_tasks.build_units_index_from_bundle(bundle_tex, bundle_entries)
        units = units_index[f1.resolve().as_posix()]

        labels = [u.get("source_label") for u in units]
        envs = [u.get("env") for u in units]
        self.assertIn("thm:in", labels)
        self.assertIn("sec:outside", labels)
        self.assertTrue("label_anchor" in envs or "gap_note" in envs)
        self.assertNotIn("eq:nested", labels)

    def test_emit_bundle_ignores_template_like_invalid_labels(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        tex_dir = self.repo_root / "src_invalid_label"
        tex_dir.mkdir(parents=True, exist_ok=True)
        f1 = tex_dir / "a.tex"
        f1.write_text(
            "\\newcommand{\\foo}[1]{\\label{#1}}\n"
            "\\section{S}\\label{sec:ok}\n",
            encoding="utf-8",
        )

        bundle_tex, bundle_entries = emit_tasks.build_tex_bundle([f1])
        units_index = emit_tasks.build_units_index_from_bundle(bundle_tex, bundle_entries)
        labels = [u.get("source_label") for u in units_index[f1.resolve().as_posix()]]
        self.assertIn("sec:ok", labels)
        self.assertNotIn("#1", labels)

    def test_emit_normalize_latexpand_explain_markers(self) -> None:
        raw = (
            "\\begin{remark}\n"
            "% start input /abs/a.tex\n"
            "Body.\n"
            "  % end input /abs/a.tex\n"
            "\\end{remark}\n"
        )
        cleaned = emit_tasks.normalize_latexpand_artifacts_with_ast(raw)
        self.assertNotIn("% start input", cleaned)
        self.assertNotIn("% end input", cleaned)
        self.assertIn("Body.", cleaned)

    def test_emit_normalize_latexpand_collapses_verb_expanded_input(self) -> None:
        raw = (
            "\\begin{remark}\n"
            "\\verb|% start input /abs/a.tex\n"
            "A\n"
            "B\n"
            "% end input /abs/a.tex\n"
            "\\end{remark}\n"
        )
        cleaned = emit_tasks.normalize_latexpand_artifacts_with_ast(raw)
        self.assertIn("\\verb|\\input{/abs/a.tex}|", cleaned)
        self.assertNotIn("% start input", cleaned)
        self.assertNotIn("% end input", cleaned)

    def test_emit_strip_gap_structural_lines(self) -> None:
        raw = (
            "\\documentclass{article}\n"
            "\\usepackage{amsmath}\n"
            "\\@ifundefined{FASTBUILD}{\\usepackage{graphicx}}{\\usepackage[draft]{graphicx}}\n"
            "\\makeatletter\\begin{document}\n"
            "\\begin{abstract}A\\end{abstract}\n"
            "\\section{Intro}\\label{sec:intro}\n"
            "Body line.\n"
            "\\end{document}\n"
        )
        cleaned, dropped = emit_tasks.strip_gap_structural_lines(raw)
        self.assertTrue(dropped)
        self.assertNotIn("\\documentclass", cleaned)
        self.assertNotIn("\\usepackage", cleaned)
        self.assertNotIn("\\@ifundefined", cleaned)
        self.assertNotIn("\\begin{document}", cleaned)
        self.assertTrue(cleaned.lstrip().startswith("\\section{Intro}"))
        self.assertIn("\\section{Intro}", cleaned)
        self.assertIn("Body line.", cleaned)

    def test_emit_gap_units_drop_structural_preamble_lines(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        tex = (
            "\\documentclass{article}\n"
            "\\usepackage{amsmath}\n"
            "\\begin{document}\n"
            "\\section{Intro}\\label{sec:intro}\n"
            "Intro text.\n"
            "\\begin{theorem}\\label{thm:a}A\\end{theorem}\n"
            "\\end{document}\n"
        )
        units = emit_tasks.extract_tex_knowledge_units(tex, "sample")
        gap_units = [u for u in units if u.get("env") == "gap_note"]
        self.assertTrue(gap_units)
        self.assertTrue(
            any(u.get("payload_normalizer_version") == "gap-structural-strip-v1" for u in gap_units)
        )
        for unit in gap_units:
            unit_tex = str(unit.get("unit_tex") or "")
            self.assertNotIn("\\documentclass", unit_tex)
            self.assertNotIn("\\usepackage", unit_tex)
            self.assertNotIn("\\begin{document}", unit_tex)

    def test_emit_marks_payload_normalizer_for_broken_verb_input(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        tex = (
            "\\begin{remark}\\label{rem:badverb}\n"
            "\\verb|% start input /abs/a.tex\n"
            "A\n"
            "\\end{remark}\n"
        )
        units = emit_tasks.extract_tex_knowledge_units(tex, "sample")
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["env"], "remark")
        self.assertEqual(units[0].get("payload_normalizer_version"), "tex-verb-sanitize-v1")

    def test_emit_merged_only_splits_oversized_gap_and_keeps_non_gap(self) -> None:
        huge_unit = {
            "env": "gap_note",
            "node_type": "tp-note",
            "source_label": "rem:ok",
            "canonical_label": "rem-ok",
            "source_refs": [],
            "unit_tex": "x" * 250000,
            "source_path": "/tmp/nonexistent.tex",
        }
        huge_non_gap = {
            "env": "remark",
            "node_type": "tp-note",
            "source_label": "rem:keep",
            "canonical_label": "rem-keep",
            "source_refs": [],
            "unit_tex": "\\begin{remark}" + ("y" * 250000) + "\\end{remark}\n",
            "source_path": "/tmp/nonexistent.tex",
        }
        filtered, stats = emit_tasks.enforce_merged_only_unit_limits(
            [huge_unit, huge_non_gap], max_unit_tex_chars=200000
        )
        self.assertGreaterEqual(len(filtered), 2)
        self.assertEqual(stats["oversized_split"], 1)
        self.assertEqual(stats["oversized_kept"], 1)
        self.assertEqual(stats["oversized_dropped"], 0)

    def test_emit_skips_suspicious_huge_target_env_and_recurses_nested(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        huge_body = "x" * (emit_tasks.SUSPICIOUS_TARGET_ENV_CHARS + 1000)
        tex = (
            "\\begin{remark}\\label{rem:outer}\n"
            + huge_body
            + "\n\\begin{theorem}\\label{thm:inside}I\\end{theorem}\n"
            "\\end{remark}\n"
        )
        units = emit_tasks.extract_tex_knowledge_units(tex, "sample")
        envs = [u.get("env") for u in units]
        self.assertIn("theorem", envs)
        self.assertTrue(any(u.get("source_label") == "thm:inside" for u in units))
        self.assertFalse(
            any(u.get("env") == "remark" and u.get("source_label") == "rem:outer" for u in units)
        )

    def test_emit_chunk_gap_text_respects_size_limit(self) -> None:
        fragment = ("Para A.\n\n" * 12000).strip()
        chunks = emit_tasks._chunk_gap_text(fragment, max_chars=5000)
        self.assertTrue(chunks)
        self.assertTrue(all(len(c) <= 5001 for c in chunks))

    def test_emit_merged_only_drops_unsplittable_oversized_gap(self) -> None:
        giant = {
            "env": "gap_note",
            "node_type": "tp-note",
            "source_label": "",
            "canonical_label": "gap",
            "source_refs": [],
            "unit_tex": "z" * 250000,
            "source_path": "/tmp/nonexistent.tex",
        }
        filtered, stats = emit_tasks.enforce_merged_only_unit_limits(
            [giant], max_unit_tex_chars=200000
        )
        self.assertTrue(filtered)
        self.assertEqual(stats["oversized_split"], 1)

    def test_emit_merged_only_keeps_oversized_non_gap(self) -> None:
        huge_non_gap = {
            "env": "remark",
            "node_type": "tp-note",
            "source_label": "rem:keep",
            "canonical_label": "rem-keep",
            "source_refs": [],
            "unit_tex": "\\begin{remark}" + ("y" * 250000) + "\\end{remark}\n",
            "source_path": "/tmp/nonexistent.tex",
        }
        filtered, stats = emit_tasks.enforce_merged_only_unit_limits(
            [huge_non_gap], max_unit_tex_chars=200000
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(stats["oversized_kept"], 1)
        self.assertEqual(stats["oversized_dropped"], 0)

    def test_emit_legacy_oversized_drop_behavior_removed(self) -> None:
        huge_unit = {
            "env": "remark",
            "node_type": "tp-note",
            "source_label": "rem:ok",
            "canonical_label": "rem-ok",
            "source_refs": [],
            "unit_tex": "\\begin{remark}" + ("x" * 250000) + "\\end{remark}\n",
            "source_path": "/tmp/nonexistent.tex",
        }
        filtered, stats = emit_tasks.enforce_merged_only_unit_limits(
            [huge_unit], max_unit_tex_chars=200000
        )
        self.assertEqual(stats["oversized_dropped"], 0)
        self.assertEqual(len(filtered), 1)

    def test_emit_build_units_index_from_bundle_does_not_require_source_file(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        missing_src = (self.repo_root / "missing_source.tex").resolve()
        bundle_tex = "\\begin{theorem}\\label{thm:cross}Recovered.\\end{theorem}\n"
        bundle_entries = [
            {
                "path": missing_src.as_posix(),
                "start": 0,
                "end": len(bundle_tex),
            }
        ]
        units_index = emit_tasks.build_units_index_from_bundle(bundle_tex, bundle_entries)
        self.assertIn(missing_src.as_posix(), units_index)
        units = units_index[missing_src.as_posix()]
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["env"], "theorem")
        self.assertEqual(units[0]["source_label"], "thm:cross")

    def test_build_index_unwrap_document_body_keeps_multiple_segments(self) -> None:
        raw = (
            "preamble\n"
            "\\begin{document}\n"
            "A\\label{sec:one}\n"
            "\\end{document}\n"
            "middle\n"
            "\\begin{document}\n"
            "\\section{S}\\label{sec:two}\n"
            "\\end{document}\n"
        )
        body = build_index.unwrap_document_body(raw)
        self.assertIn("\\label{sec:one}", body)
        self.assertIn("\\label{sec:two}", body)
        self.assertNotIn("\\begin{document}", body)
        self.assertNotIn("\\end{document}", body)

    def test_build_index_source_order_uses_merged_map_and_task_seq(self) -> None:
        a = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="a",
            atom_type="tp-note",
            ext="tex",
            content="A\n",
        )
        b = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="b",
            atom_type="tp-note",
            ext="tex",
            content="B\n",
        )

        src1 = (self.repo_root / "paper" / "sec1.tex").resolve()
        src2 = (self.repo_root / "paper" / "sec2.tex").resolve()
        src1.parent.mkdir(parents=True, exist_ok=True)
        src1.write_text("sec1\n", encoding="utf-8")
        src2.write_text("sec2\n", encoding="utf-8")

        common.atom_sidecar_path(a).write_text(
            json.dumps(
                {
                    "kg_id": "KG-20260303-0001",
                    "label": "a",
                    "atom_type": "tp-note",
                    "parents": [],
                    "source_path": src2.as_posix(),
                    "task_id": "TASK-20260304T000000Z-000200",
                }
            ),
            encoding="utf-8",
        )
        common.atom_sidecar_path(b).write_text(
            json.dumps(
                {
                    "kg_id": "KG-20260303-0002",
                    "label": "b",
                    "atom_type": "tp-note",
                    "parents": [],
                    "source_path": src1.as_posix(),
                    "task_id": "TASK-20260304T000000Z-000100",
                }
            ),
            encoding="utf-8",
        )

        merged_dir = self.kg_root / ".kgcache" / "merged"
        merged_dir.mkdir(parents=True, exist_ok=True)
        merged_map = merged_dir / "m.map.json"
        merged_map.write_text(
            json.dumps(
                {
                    "entries": [
                        {"path": src2.as_posix(), "start": 200, "end": 260},
                        {"path": src1.as_posix(), "start": 100, "end": 150},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (merged_dir / "emit_state.json").write_text(
            json.dumps({"merged_map_path": merged_map.as_posix()}),
            encoding="utf-8",
        )

        atoms, errors = common.scan_atoms(self.kg_root, verify_hash=False)
        self.assertEqual(errors, [])
        ordered = build_index.order_atoms_by_source_position(self.kg_root, atoms)
        self.assertEqual([a.label for a in ordered], ["b", "a"])

    def test_emit_resolve_merged_paths_requires_explicit_existing_inputs(self) -> None:
        merged_tex = self.repo_root / "merged.tex"
        merged_map = self.repo_root / "merged.map.json"

        with self.assertRaises(RuntimeError):
            emit_tasks.resolve_merged_paths(merged_tex, merged_map)

        merged_tex.write_text("% merged\n", encoding="utf-8")
        merged_map.write_text(
            json.dumps({"entries": [{"path": str(merged_tex), "start": 0, "end": 8}]}),
            encoding="utf-8",
        )
        tex_p, map_p = emit_tasks.resolve_merged_paths(merged_tex, merged_map)
        self.assertEqual(tex_p, merged_tex.resolve())
        self.assertEqual(map_p, merged_map.resolve())

    def test_latexpand_entry_parser_tracks_source_segments(self) -> None:
        main_tex = (self.repo_root / "paper" / "main.tex").resolve()
        expanded = (
            "P0\n"
            "% start input sections/a.tex\n"
            "A1\n"
            "A2\n"
            "% end input sections/a.tex\n"
            "P1\n"
            "% start input sections/b.tex\n"
            "B1\n"
            "% end input sections/b.tex\n"
            "P2\n"
        )
        entries = latexpand_merge.parse_latexpand_entries(expanded, main_tex)
        self.assertGreaterEqual(len(entries), 3)
        self.assertEqual(entries[0]["path"], main_tex.as_posix())
        sources = [str(e["path"]) for e in entries]
        self.assertIn((main_tex.parent / "sections" / "a.tex").resolve().as_posix(), sources)
        self.assertIn((main_tex.parent / "sections" / "b.tex").resolve().as_posix(), sources)

    def test_latexpand_expand_residual_inputs_from_mapped_source(self) -> None:
        if not HAS_PYLATEXENC:
            self.skipTest("pylatexenc not available")

        paper = (self.repo_root / "paper").resolve()
        sections = paper / "sections"
        sections.mkdir(parents=True, exist_ok=True)
        main_tex = paper / "main.tex"
        main_tex.write_text("\\input{sections/a}\n", encoding="utf-8")

        a_tex = sections / "a.tex"
        a_tex.write_text("\\input{b}\\input{c}\n", encoding="utf-8")
        (sections / "b.tex").write_text("\\label{thm:from-b}\n", encoding="utf-8")
        (sections / "c.tex").write_text("\\label{thm:from-c}\n", encoding="utf-8")

        merged = (
            "% start input sections/a.tex\n"
            "\\input{b}\\input{c}\n"
            "% end input sections/a.tex\n"
        )
        expanded, expanded_count, unresolved = latexpand_merge.expand_residual_inputs(
            merged,
            main_tex=main_tex,
        )
        self.assertGreaterEqual(expanded_count, 2)
        self.assertEqual(unresolved, 0)
        self.assertIn("\\label{thm:from-b}", expanded)
        self.assertIn("\\label{thm:from-c}", expanded)
        self.assertNotIn("\\input{b}", expanded)
        self.assertNotIn("\\input{c}", expanded)

    def test_ingest_non_dry_run_creates_atom_file(self) -> None:
        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)

        task = {
            "task_id": "TASK-1",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "added",
            "source_path": "",
            "old_hash": None,
            "new_hash": "abc",
            "diff_excerpt": "hello world",
            "candidate_parent_labels": [],
            "suggested_node_type": "tp-claim",
            "proposed_label": "sample-claim",
            "status": "pending",
        }
        task_path = queue / "task_000001.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        atom_files = list((self.kg_root / "atoms").glob("KG-*.tex"))
        self.assertEqual(len(atom_files), 1)
        parsed = common.parse_atom_filename(atom_files[0])
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[1], "sample-claim")
        self.assertEqual(parsed[2], "tp-claim")

    def test_next_kg_id_factory_uses_fixed_five_digit_width(self) -> None:
        now = datetime(2026, 3, 4, 0, 0, 0, tzinfo=timezone.utc)
        next_id = ingest_atoms.next_kg_id_factory(self.kg_root, now)
        self.assertEqual(next_id(), "KG-20260304-00001")

        write_atom(
            self.kg_root,
            kg_id="KG-20260304-12345",
            label="existing-seq",
            atom_type="tp-note",
            ext="txt",
            content="x\n",
        )
        next_after_existing = ingest_atoms.next_kg_id_factory(self.kg_root, now)
        self.assertEqual(next_after_existing(), "KG-20260304-12346")

    def test_ingest_tex_knowledge_unit_resolves_parents(self) -> None:
        parent_label = "lem-base-h111111111111"
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label=parent_label,
            atom_type="tp-lemma",
            parents=tuple(),
            ext="tex",
            content="\\begin{lemma}\\label{kg:lem-base-h111111111111}Base\\end{lemma}\n",
        )

        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": "TASK-TEX-1",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "modified",
            "source_path": str(self.repo_root / "paper.tex"),
            "old_hash": "abc",
            "new_hash": "def",
            "suggested_node_type": "tp-thm",
            "task_kind": "tex_knowledge_unit",
            "canonical_label": "thm-main",
            "source_tex_label": "thm:main",
            "source_refs": ["lem:base"],
            "unit_tex": "\\begin{theorem}\\label{thm:main}By \\ref{lem:base}.\\end{theorem}",
            "status": "pending",
        }
        task_path = queue / "task_000001.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        atom_files = sorted((self.kg_root / "atoms").glob("KG-*.tex"))
        self.assertEqual(len(atom_files), 2)
        created = atom_files[-1]
        parsed = common.parse_atom_filename(created)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed[1].startswith("thm-main-h"))
        self.assertEqual(parsed[2], "tp-thm")
        atoms, scan_errors = common.scan_atoms(self.kg_root)
        self.assertEqual(scan_errors, [])
        by_label = {a.label: a for a in atoms}
        self.assertIn(parsed[1], by_label)
        self.assertEqual(by_label[parsed[1]].parents, (parent_label,))

    def test_ingest_compute_tex_task_label_can_use_payload_normalizer_version(self) -> None:
        base_task = {
            "canonical_label": "proof-main",
            "source_tex_label": "proof:main",
            "unit_tex": "\\begin{proof}A\\end{proof}\n",
        }
        old_label = ingest_atoms.compute_tex_task_label(base_task)
        new_label = ingest_atoms.compute_tex_task_label(
            {
                **base_task,
                "payload_normalizer_version": "proof-env-preserve-v1",
            }
        )
        self.assertNotEqual(old_label, new_label)
        self.assertTrue(old_label.startswith("proof-main-h"))
        self.assertTrue(new_label.startswith("proof-main-h"))

    def test_ingest_tex_unit_resolves_parent_via_source_label_alias(self) -> None:
        parent_label = "opaque-parent-h111111111111"
        parent_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label=parent_label,
            atom_type="tp-lemma",
            parents=tuple(),
            ext="tex",
            content="\\begin{lemma}Base\\end{lemma}\n",
        )
        common.write_json(
            common.atom_sidecar_path(parent_path),
            {
                "kg_id": "KG-20260303-0001",
                "label": parent_label,
                "atom_type": "tp-lemma",
                "parents": [],
                "source_tex_label": "lem:legacy-base",
            },
        )

        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": "TASK-TEX-ALIAS-1",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "modified",
            "source_path": str(self.repo_root / "paper.tex"),
            "old_hash": "abc",
            "new_hash": "def",
            "suggested_node_type": "tp-thm",
            "task_kind": "tex_knowledge_unit",
            "canonical_label": "thm-main",
            "source_tex_label": "thm:main",
            "source_refs": ["lem:legacy-base"],
            "unit_tex": "\\begin{theorem}\\label{thm:main}By \\ref{lem:legacy-base}.\\end{theorem}",
            "status": "pending",
        }
        task_path = queue / "task_000011.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        atoms, scan_errors = common.scan_atoms(self.kg_root)
        self.assertEqual(scan_errors, [])
        created = [a for a in atoms if a.label.startswith("thm-main-h")]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].parents, (parent_label,))

    def test_ingest_tex_knowledge_unit_sanitizes_orphan_fi(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="lem-base-h111111111111",
            atom_type="tp-lemma",
            parents=tuple(),
            ext="tex",
            content="\\begin{lemma}\\label{kg:lem-base-h111111111111}Base\\end{lemma}\n",
        )
        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": "TASK-TEX-2",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "modified",
            "source_path": str(self.repo_root / "paper.tex"),
            "old_hash": "abc",
            "new_hash": "def",
            "suggested_node_type": "tp-proof",
            "task_kind": "tex_knowledge_unit",
            "canonical_label": "proof-main",
            "source_tex_label": "",
            "source_refs": ["lem:base"],
            "unit_env": "proof",
            "unit_tex": "\\begin{proof}X\\end{proof}\n\\ifnum1=1\n\\fi\n",
            "status": "pending",
        }
        task_path = queue / "task_000002.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        atom_files = sorted((self.kg_root / "atoms").glob("KG-*.tex"))
        self.assertEqual(len(atom_files), 2)
        content = atom_files[-1].read_text(encoding="utf-8")
        self.assertNotIn("\n\\fi\n", content)
        self.assertNotIn("\n\\ifnum1=1\n", content)
        self.assertIn("\\begin{proof}", content)
        self.assertIn("\\end{proof}", content)

    def test_ingest_tex_knowledge_unit_repairs_unbalanced_envs(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="lem-base-h111111111111",
            atom_type="tp-lemma",
            parents=tuple(),
            ext="tex",
            content="\\begin{lemma}\\label{kg:lem-base-h111111111111}Base\\end{lemma}\n",
        )
        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": "TASK-TEX-3",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "modified",
            "source_path": str(self.repo_root / "paper.tex"),
            "old_hash": "abc",
            "new_hash": "def",
            "suggested_node_type": "tp-proof",
            "task_kind": "tex_knowledge_unit",
            "canonical_label": "proof-unbalanced",
            "source_tex_label": "",
            "source_refs": ["lem:base"],
            "unit_env": "proof",
            "unit_tex": "\\begin{proof}A\\begin{remark}B\\end{remark}\n",
            "status": "pending",
        }
        task_path = queue / "task_000003.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        atom_files = sorted((self.kg_root / "atoms").glob("KG-*.tex"))
        self.assertEqual(len(atom_files), 2)
        content = atom_files[-1].read_text(encoding="utf-8")
        self.assertIn("\\begin{proof}", content)
        self.assertIn("\\begin{remark}", content)
        self.assertIn("\\end{remark}", content)
        self.assertIn("\\end{proof}", content)

    def test_ingest_sanitizes_unclosed_verb_line(self) -> None:
        raw = (
            "\\begin{remark}\n"
            "See \\verb|/tmp/demo\n"
            "\\end{remark}\n"
        )
        norm = ingest_atoms.normalize_tex_fragment(raw, preserve_proof_env=False)
        self.assertNotIn("\\verb|/tmp/demo", norm)
        self.assertIn("\\texttt{", norm)

    def test_ingest_keeps_orphan_proof_atom_with_root_parent(self) -> None:
        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": "TASK-TEX-ORPHAN-PROOF",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "modified",
            "source_path": str(self.repo_root / "paper.tex"),
            "old_hash": "abc",
            "new_hash": "def",
            "suggested_node_type": "tp-proof",
            "task_kind": "tex_knowledge_unit",
            "canonical_label": "proof-orphan",
            "source_tex_label": "",
            "source_refs": [],
            "unit_tex": "\\begin{proof}orphan\\end{proof}\n",
            "status": "pending",
        }
        task_path = queue / "task_000099.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
        atom_files = sorted((self.kg_root / "atoms").glob("KG-*.tex"))
        self.assertEqual(len(atom_files), 1)
        meta = json.loads(common.atom_sidecar_path(atom_files[0]).read_text(encoding="utf-8"))
        self.assertEqual(meta.get("atom_type"), "tp-proof")
        self.assertEqual(meta.get("parents"), [])
        self.assertTrue(bool(meta.get("proof_orphan")))

    def test_ingest_generic_tex_wraps_lonely_item(self) -> None:
        source = self.repo_root / "frag.tex"
        source.write_text("\\item one\n\\item two\n", encoding="utf-8")

        queue = self.kg_root / ".kgcache" / "llm_queue"
        queue.mkdir(parents=True, exist_ok=True)
        task = {
            "task_id": "TASK-TEX-4",
            "created_at": "20260303T000000Z",
            "source_name": "test",
            "change_type": "modified",
            "source_path": str(source),
            "old_hash": "abc",
            "new_hash": "def",
            "suggested_node_type": "tp-claim",
            "proposed_label": "frag-claim",
            "status": "pending",
        }
        task_path = queue / "task_000004.json"
        task_path.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")

        cmd = [
            "python3",
            str((SCRIPT_DIR / "kg_ingest_atoms.py").resolve()),
            "--kg-root",
            str(self.kg_root),
            "--task",
            str(task_path),
            "--limit",
            "1",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)

        atom_files = sorted((self.kg_root / "atoms").glob("KG-*.tex"))
        self.assertEqual(len(atom_files), 1)
        content = atom_files[0].read_text(encoding="utf-8")
        self.assertIn("\\begin{itemize}", content)
        self.assertIn("\\item one", content)
        self.assertIn("\\end{itemize}", content)

    def test_build_index_and_collect_compile_inputs(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="base",
            atom_type="tp-def",
            ext="tex",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="method",
            atom_type="tp-method",
            parents=("base",),
            ext="py",
            content="print('ok')\n",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0003",
            label="result",
            atom_type="tp-exp",
            parents=("base",),
            ext="tex",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0004",
            label="rootdoc",
            atom_type="tp-note",
            parents=("result",),
            ext="tex",
            content=(
                "\\documentclass[../main.tex]{subfiles}\n"
                "\\begin{document}\n"
                "\\label{kg:rootdoc}\n"
                "root\n"
                "\\end{document}\n"
            ),
        )

        spec = self.kg_root / "index_specs" / "book.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: book",
                    "roots: rootdoc",
                    "include_types: tp-def,tp-exp,tp-method,tp-note",
                    "auto_include_methods: false",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        content = out_tex.read_text(encoding="utf-8")
        self.assertIn("\\kginput{", content)
        self.assertIn("result", content)
        self.assertNotIn("tp-method", content)
        self.assertIn("mode=sanitized", content)
        manifest = json.loads((out_tex.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("selection_fingerprint", manifest)
        self.assertEqual(manifest["sanitized_tex_atom_count"], 1)

        mtime_before = out_tex.stat().st_mtime_ns
        time.sleep(1.1)
        out_tex_2 = build_index.build_single_spec(self.kg_root, spec)
        mtime_after = out_tex_2.stat().st_mtime_ns
        self.assertEqual(out_tex_2, out_tex)
        self.assertEqual(mtime_before, mtime_after)
        alias_dir = out_tex.parent / "atoms"
        one_alias = next(alias_dir.glob("KG-*.tex"))
        one_alias.unlink()
        time.sleep(1.1)
        out_tex_3 = build_index.build_single_spec(self.kg_root, spec)
        self.assertEqual(out_tex_3, out_tex)
        self.assertTrue(one_alias.exists())
        self.assertGreater(out_tex_3.stat().st_mtime_ns, mtime_after)

        inputs, skipped = kg_compile.collect_tex_atoms_for_label(self.kg_root, "rootdoc")
        self.assertEqual(len(inputs), 2)
        self.assertEqual(len(skipped), 1)
        input_labels = [common.parse_atom_filename(Path(p))[1] for p in inputs]
        self.assertEqual(input_labels, ["base", "result"])
        skipped_label = common.parse_atom_filename(Path(skipped[0][0]))[1]
        self.assertEqual(skipped_label, "rootdoc")

    def test_compile_template_stable_mode_ref_suppression(self) -> None:
        template = kg_compile.build_main_tex(
            [Path("/tmp/dummy.tex")],
            fragment_ref_mode=True,
        )
        self.assertIn("\\def\\@setref", template)
        self.assertIn("\\hbadness=10000", template)
        self.assertIn("\\hfuzz=1000pt", template)
        self.assertNotIn("\\renewcommand{\\ref}", template)
        self.assertNotIn("\\renewcommand{\\cite}", template)

        template_degrade_cite = kg_compile.build_main_tex(
            [Path("/tmp/dummy.tex")],
            fragment_ref_mode=True,
            degrade_cite=True,
        )
        self.assertIn("\\renewcommand{\\cite}", template_degrade_cite)

    def test_compile_extracts_bibliography_tail_from_merged(self) -> None:
        merged = self.repo_root / "merged.latexpanded.tex"
        merged.write_text(
            "\n".join(
                [
                    "Body",
                    "\\bibliographystyle{amsplain}",
                    "\\bibliography{\\subfix{../../references},\\subfix{../../refs_extra.bib},custom_refs}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        source_main = (self.repo_root / "paper" / "main.tex").resolve()
        source_main.parent.mkdir(parents=True, exist_ok=True)
        source_main.write_text("\\documentclass{ctexart}\n\\begin{document}\\end{document}\n", encoding="utf-8")

        tail = kg_compile.extract_bibliography_tail_lines(merged, source_main)
        self.assertEqual(tail[0], "\\bibliographystyle{amsplain}")
        self.assertEqual(
            tail[1],
            "\\bibliography{"
            + ",".join(
                [
                    (source_main.parent / "../../references").resolve().as_posix(),
                    (source_main.parent / "../../refs_extra").resolve().as_posix(),
                    (source_main.parent / "custom_refs").resolve().as_posix(),
                ]
            )
            + "}",
        )

    def test_compile_discover_merged_tex_from_emit_state(self) -> None:
        merged_dir = self.kg_root / ".kgcache" / "merged"
        merged_dir.mkdir(parents=True, exist_ok=True)
        merged_path = merged_dir / "grg_main.latexpanded.tex"
        merged_path.write_text("% merged\n", encoding="utf-8")
        state_path = merged_dir / "emit_state.json"
        state_path.write_text(
            json.dumps({"merged_tex_path": merged_path.as_posix()}, ensure_ascii=False),
            encoding="utf-8",
        )

        found = kg_compile.discover_merged_tex_from_emit_state(self.kg_root)
        self.assertEqual(found, merged_path.resolve())

    def test_compile_builds_missing_ref_anchor_lines_from_closure_report(self) -> None:
        idx_dir = self.kg_root / "index_nodes" / "book_grg"
        idx_dir.mkdir(parents=True, exist_ok=True)
        idx_path = idx_dir / "idx_book_grg_main.tex"
        idx_path.write_text("% index\n", encoding="utf-8")
        (idx_dir / "reference_closure_report.json").write_text(
            json.dumps(
                {
                    "final_missing_refs": [
                        "thm:missing-a",
                        "prop:missing-b",
                        "thm:missing-a",
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        lines = kg_compile.build_missing_ref_anchor_lines(idx_path)
        self.assertTrue(lines)
        self.assertIn("\\genfraglabel{thm:missing-a}", "".join(lines))
        self.assertIn("\\genfraglabel{prop:missing-b}", "".join(lines))

    def test_compile_extracts_dag_bibliography_tail_lines(self) -> None:
        bib_dir = self.kg_root / "bibliography"
        bib_dir.mkdir(parents=True, exist_ok=True)
        (bib_dir / "references.bib").write_text("@book{a,title={A}}\n", encoding="utf-8")
        (bib_dir / "zeta.bib").write_text("@book{z,title={Z}}\n", encoding="utf-8")

        lines = kg_compile.extract_dag_bibliography_tail_lines(self.kg_root)
        self.assertTrue(lines)
        self.assertEqual(lines[0], "\\bibliographystyle{amsplain}")
        self.assertIn("\\bibliography{", lines[1])
        self.assertIn((bib_dir / "references").resolve().as_posix(), lines[1])
        self.assertIn((bib_dir / "zeta").resolve().as_posix(), lines[1])

    def test_compile_rewrite_ref_aliases(self) -> None:
        text = (
            "See \\ref{cor:old} and \\cref{thm:keep,thm:old}.\n"
            "Also \\eqref{eq:old}.\n"
        )
        out = kg_compile.rewrite_ref_aliases(
            text,
            {
                "cor:old": "thm:new",
                "thm:old": "thm:new2",
                "eq:old": "eq:new",
            },
        )
        self.assertIn("\\ref{thm:new}", out)
        self.assertIn("\\cref{thm:keep,thm:new2}", out)
        self.assertIn("\\eqref{eq:new}", out)

    def test_compile_build_packed_index_input_applies_ref_aliases(self) -> None:
        idx_dir = self.repo_root / "idx"
        atoms_dir = idx_dir / "atoms"
        atoms_dir.mkdir(parents=True, exist_ok=True)
        atom_path = atoms_dir / "KG-20260303-00001.tex"
        atom_path.write_text(
            "\\begin{theorem}\\label{thm:src}By \\ref{cor:old}.\\end{theorem}\n",
            encoding="utf-8",
        )

        index_path = idx_dir / "idx_test_main.tex"
        index_path.write_text(
            "\\kginput{atoms/KG-20260303-00001.tex}\n",
            encoding="utf-8",
        )
        build_dir = self.repo_root / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        packed = kg_compile.build_packed_index_input(
            index_path,
            build_dir,
            alias_map={"cor:old": "thm:new"},
        )
        content = packed.read_text(encoding="utf-8")
        self.assertIn("\\ref{thm:new}", content)
        self.assertNotIn("\\ref{cor:old}", content)

    def test_compile_normalize_repairs_nested_display_math_delimiters(self) -> None:
        raw = (
            "\\[\n"
            "\\begin{aligned}\n"
            "a&=b\n"
            "\\[\n"
            "\\begin{aligned}\n"
            "c&=d\n"
            "\\end{aligned}\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertEqual(normalized.count("\\["), normalized.count("\\]"))
        self.assertIn("a&=b\n\\end{aligned}\\]\\[", normalized)

    def test_compile_normalize_closes_aligned_before_prose(self) -> None:
        raw = (
            "\\[\n"
            "\\begin{aligned}\n"
            "a&=b\\\\\n"
            "\n"
            "中文说明\n"
            "\\[\n"
            "c=d\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\end{aligned}\\]", normalized)
        self.assertIn("中文说明", normalized)
        self.assertEqual(normalized.count("\\["), normalized.count("\\]"))

    def test_compile_normalize_drops_orphan_aligned_end(self) -> None:
        raw = (
            "Text.\n"
            "\\[\n"
            "a=b\n"
            "\\]\n"
            "\\end{aligned}\n"
            "Next.\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertNotIn("\\end{aligned}\n", normalized)
        self.assertIn("Next.", normalized)

    def test_compile_normalize_repairs_inline_paren_matrix_balance(self) -> None:
        raw = (
            "\\(\n"
            "\\begin{pmatrix}\n"
            "1 & 2\\\\\n"
            "3 & 4\n"
            "\\)\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\end{pmatrix}\\)", normalized)

    def test_compile_normalize_keeps_matrix_row_spacing_command(self) -> None:
        raw = (
            "\\[\n"
            "A=\\begin{pmatrix}1&1\\\\[2pt]1&0\\end{pmatrix}\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\\\[2pt]", normalized)
        self.assertNotIn("\\]\\[2pt]", normalized)

    def test_compile_normalize_repairs_cases_before_equation_end(self) -> None:
        raw = (
            "\\begin{equation}\n"
            "x=\\begin{cases}\n"
            "1,&a\\\\\n"
            "2,&b\n"
            "\\end{equation}\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\end{cases}\\end{equation}", normalized)

    def test_compile_normalize_keeps_cases_end_when_balanced(self) -> None:
        raw = (
            "\\begin{equation}\n"
            "\\begin{cases}\n"
            "1,&a\\\\\n"
            "2,&b\n"
            "\\end{cases}\n"
            "\\end{equation}\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\end{cases}", normalized)

    def test_compile_normalize_second_pass_drops_new_orphan_aligned(self) -> None:
        raw = (
            "\\[\n"
            "\\begin{aligned}\n"
            "a&=b\n"
            "中文\n"
            "\\[\n"
            "\\begin{aligned}\n"
            "c&=d\n"
            "\\end{aligned}\n"
            "\\]\n"
            "\\end{aligned}\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\end{aligned}\\]\\[", normalized)
        self.assertFalse(normalized.rstrip().endswith("\\end{aligned}"))

    def test_compile_normalize_flattens_nested_inline_math_in_display(self) -> None:
        raw = (
            "\\[\n"
            "x=\\text{\\(a^2-a+1=0\\) 的根}\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("x=\\text{(a\\^2-a+1=0) 的根}", normalized)
        self.assertNotIn("\\(a^2-a+1=0\\)", normalized)

    def test_compile_normalize_rewrites_text_macro_embedded_math_with_cjk(self) -> None:
        raw = (
            "\\[\n"
            "\\QQ\\bigl(\\text{(P_{\\mathrm{LY}}(y)) 的全部根}\\bigr)\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\text{$(P_{\\mathrm{LY}}(y))$ 的全部根}", normalized)

    def test_compile_normalize_escapes_underscore_in_text_macro(self) -> None:
        raw = (
            "\\[\n"
            "\\text{Kodaira 型 (I_2)}\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\text{Kodaira 型 (I\\_2)}", normalized)

    def test_compile_normalize_drops_endinput_terminator(self) -> None:
        raw = (
            "\\paragraph{A}\\label{a}\n"
            "\\endinput\n"
            "\\paragraph{B}\\label{b}\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertNotIn("\\endinput", normalized)
        self.assertIn("\\label{a}", normalized)
        self.assertIn("\\label{b}", normalized)

    def test_compile_normalize_drops_latexpand_artifact_text_lines(self) -> None:
        raw = (
            "\\paragraph{A}\n"
            "\\texttt{\\% start input /Users/auric/project/sections/a.tex}\n"
            "real content\n"
            "% end input /Users/auric/project/sections/a.tex\n"
            "\\paragraph{B}\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertNotIn("start input /Users/auric/project/sections/a.tex", normalized)
        self.assertNotIn("end input /Users/auric/project/sections/a.tex", normalized)
        self.assertIn("real content", normalized)
        self.assertIn("\\paragraph{B}", normalized)

    def test_compile_normalize_degrades_math_macros_inside_cjk_text_macro(self) -> None:
        raw = (
            "\\[\n"
            "\\text{作为置换 (c_\\ell\\in\\mathrm{Sym}(\\mathsf{Ind}(P_\\ell))) 的阶}\n"
            "\\]\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\text{作为置换 (c\\_ell in Sym(Ind(P\\_ell))) 的阶}", normalized)
        self.assertNotIn("\\mathrm{", normalized)
        self.assertNotIn("\\mathsf{", normalized)

    def test_compile_normalize_keeps_outer_inline_math_when_inner_inline_in_text(self) -> None:
        raw = (
            "此外：对每个 \\(\\alpha\\in\\{\\text{\\(a^2-a+1=0\\) 的根}\\}\\)，两点对应。\n"
        )
        normalized = kg_compile.normalize_atom_tex_for_packed_index(raw)
        self.assertIn("\\text{(a\\^2-a+1=0) 的根}", normalized)
        self.assertIn("\\}\\)，两点对应", normalized)

    def test_extract_tex_crossrefs_ignores_comments(self) -> None:
        tex = (
            "\\label{sec:ok}\n"
            "% \\label{sec:commented}\n"
            "By \\ref{sec:ok,sec:next} and \\eqref{eq:one}. % \\ref{sec:hidden}\n"
            "\\cite{A1, B2}\n"
        )
        labels, refs, cites = common.extract_tex_crossrefs(tex)
        self.assertEqual(labels, {"sec:ok", "sec__ok"})
        self.assertEqual(refs, {"sec:ok", "sec:next", "eq:one"})
        self.assertEqual(cites, {"A1", "B2"})

    def test_extract_tex_crossrefs_supports_genfraglabel_and_colon_alias(self) -> None:
        tex = (
            "\\genfraglabel{tab:demo}\n"
            "See \\ref{subsubsec__fold-zeckendorf-mod-topbits}.\n"
        )
        labels, refs, _ = common.extract_tex_crossrefs(tex)
        self.assertIn("tab:demo", labels)
        self.assertIn("tab__demo", labels)
        self.assertIn("subsubsec__fold-zeckendorf-mod-topbits", refs)

    def test_build_index_reference_closure_adds_excluded_type(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="def-base",
            atom_type="tp-def",
            ext="tex",
            content="\\begin{definition}\\label{def:base}Base\\end{definition}\n",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="thm-main",
            atom_type="tp-thm",
            parents=("def-base",),
            ext="tex",
            content="\\begin{theorem}\\label{thm:main}Use \\ref{prop:helper}.\\end{theorem}\n",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0003",
            label="prop-helper",
            atom_type="tp-prop",
            parents=("def-base",),
            ext="tex",
            content="\\begin{proposition}\\label{prop:helper}Helper\\end{proposition}\n",
        )

        spec = self.kg_root / "index_specs" / "closure.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: closure",
                    "roots: thm-main",
                    "include_types: tp-def,tp-thm",
                    "reference_closure: true",
                    "reference_closure_max_rounds: 6",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        content = out_tex.read_text(encoding="utf-8")
        self.assertIn("thm-main", content)
        self.assertIn("prop-helper", content)

        closure_report = json.loads(
            (out_tex.parent / "reference_closure_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(closure_report["added_atom_count"], 1)
        self.assertEqual(closure_report["final_missing_ref_count"], 0)

    def test_build_index_reference_closure_resolves_alias_mapping(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0101",
            label="thm-target",
            atom_type="tp-thm",
            ext="tex",
            content="\\begin{theorem}\\label{thm:target}T\\end{theorem}\n",
        )
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0102",
            label="thm-user",
            atom_type="tp-thm",
            ext="tex",
            content="\\begin{theorem}\\label{thm:user}By \\ref{cor:target}.\\end{theorem}\n",
        )

        schema_dir = self.kg_root / "schema"
        schema_dir.mkdir(parents=True, exist_ok=True)
        (schema_dir / "reference_aliases.json").write_text(
            json.dumps({"cor:target": "thm:target"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        spec = self.kg_root / "index_specs" / "alias.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: alias",
                    "roots: thm-user",
                    "include_types: tp-thm",
                    "reference_closure: true",
                    "reference_closure_max_rounds: 4",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        closure_report = json.loads(
            (out_tex.parent / "reference_closure_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(closure_report["final_missing_ref_count"], 0)
        self.assertGreaterEqual(int(closure_report.get("resolved_by_alias_count", 0)), 1)
        self.assertEqual(closure_report.get("resolved_by_alias", {}).get("cor:target"), "thm:target")

    def test_build_index_can_filter_tex_task_kind_and_keep_latest_version_only(self) -> None:
        old_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="thm-main-h111111111111",
            atom_type="tp-thm",
            ext="tex",
            content="\\begin{theorem}\\label{thm:main-old}Old\\end{theorem}\n",
        )
        common.write_json(
            common.atom_sidecar_path(old_path),
            {
                "kg_id": "KG-20260303-0001",
                "label": "thm-main-h111111111111",
                "atom_type": "tp-thm",
                "parents": [],
                "task_kind": "tex_knowledge_unit",
            },
        )

        new_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="thm-main-h222222222222",
            atom_type="tp-thm",
            ext="tex",
            content="\\begin{theorem}\\label{thm:main-new}New\\end{theorem}\n",
        )
        common.write_json(
            common.atom_sidecar_path(new_path),
            {
                "kg_id": "KG-20260303-0002",
                "label": "thm-main-h222222222222",
                "atom_type": "tp-thm",
                "parents": [],
                "task_kind": "tex_knowledge_unit",
            },
        )

        legacy_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0003",
            label="legacy-plain",
            atom_type="tp-note",
            ext="tex",
            content="\\begin{remark}\\label{rem:legacy}Legacy\\end{remark}\n",
        )
        common.write_json(
            common.atom_sidecar_path(legacy_path),
            {
                "kg_id": "KG-20260303-0003",
                "label": "legacy-plain",
                "atom_type": "tp-note",
                "parents": [],
                "task_kind": "",
            },
        )

        spec = self.kg_root / "index_specs" / "latest_only.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: latest_only",
                    "roots:",
                    "include_types: tp-thm,tp-note",
                    "reference_closure: false",
                    "tex_task_kind_filter: tex_knowledge_unit",
                    "latest_version_only: true",
                    "order: alpha",
                ]
            ),
            encoding="utf-8",
        )

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        content = out_tex.read_text(encoding="utf-8")
        self.assertIn("thm-main-h222222222222", content)
        self.assertNotIn("thm-main-h111111111111", content)
        self.assertNotIn("legacy-plain", content)

        manifest = json.loads((out_tex.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["dropped_older_versions"], 1)
        self.assertEqual(manifest["tex_task_kind_filter"], ["tex_knowledge_unit"])

    def test_build_index_can_drop_unused_label_anchor_atoms(self) -> None:
        thm_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0001",
            label="thm-main-haaaaaaaaaaaa",
            atom_type="tp-thm",
            ext="tex",
            content=(
                "\\begin{theorem}\\label{thm:main}"
                "By \\ref{sec:keep}.\\end{theorem}\n"
            ),
        )
        common.write_json(
            common.atom_sidecar_path(thm_path),
            {
                "kg_id": "KG-20260303-0001",
                "label": "thm-main-haaaaaaaaaaaa",
                "atom_type": "tp-thm",
                "parents": [],
                "task_kind": "tex_knowledge_unit",
                "unit_env": "theorem",
            },
        )

        keep_anchor_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0002",
            label="sec-keep-hbbbbbbbbbbbb",
            atom_type="tp-note",
            ext="tex",
            content="\\label{sec:keep}\\ignorespaces\n",
        )
        common.write_json(
            common.atom_sidecar_path(keep_anchor_path),
            {
                "kg_id": "KG-20260303-0002",
                "label": "sec-keep-hbbbbbbbbbbbb",
                "atom_type": "tp-note",
                "parents": [],
                "task_kind": "tex_knowledge_unit",
                "unit_env": "label_anchor",
                "source_tex_label": "sec:keep",
            },
        )

        unused_anchor_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0003",
            label="sec-unused-hcccccccccccc",
            atom_type="tp-note",
            ext="tex",
            content="\\label{sec:unused}\\ignorespaces\n",
        )
        common.write_json(
            common.atom_sidecar_path(unused_anchor_path),
            {
                "kg_id": "KG-20260303-0003",
                "label": "sec-unused-hcccccccccccc",
                "atom_type": "tp-note",
                "parents": [],
                "task_kind": "tex_knowledge_unit",
                "unit_env": "label_anchor",
                "source_tex_label": "sec:unused",
            },
        )

        spec = self.kg_root / "index_specs" / "drop_anchors.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: drop_anchors",
                    "roots:",
                    "include_types: tp-thm,tp-note",
                    "reference_closure: false",
                    "drop_unused_label_anchors: true",
                    "order: alpha",
                ]
            ),
            encoding="utf-8",
        )

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        content = out_tex.read_text(encoding="utf-8")
        self.assertIn("thm-main-haaaaaaaaaaaa", content)
        self.assertIn("sec-keep-hbbbbbbbbbbbb", content)
        self.assertNotIn("sec-unused-hcccccccccccc", content)

        manifest = json.loads((out_tex.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["drop_unused_label_anchors"])
        self.assertEqual(manifest["dropped_unused_label_anchors"], 1)

        closure_report = json.loads(
            (out_tex.parent / "reference_closure_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(closure_report["dropped_unused_label_anchors"], 1)

    def test_build_index_sanitizes_wrapper_and_rewrites_bibliography_paths(self) -> None:
        src_dir = self.repo_root / "docs" / "sections" / "backmatter"
        src_dir.mkdir(parents=True, exist_ok=True)
        (self.repo_root / "docs" / "references_alpha.bib").write_text(
            "@article{A, title={A}}\n", encoding="utf-8"
        )
        (self.repo_root / "docs" / "references_beta.bib").write_text(
            "@article{B, title={B}}\n", encoding="utf-8"
        )
        source_file = src_dir / "main.tex"
        source_file.write_text("% src\n", encoding="utf-8")

        wrapper_path = write_atom(
            self.kg_root,
            kg_id="KG-20260303-0099",
            label="backmatter-main",
            atom_type="tp-note",
            ext="tex",
            content=(
                "\\documentclass[../../main.tex]{subfiles}\n"
                "\\begin{document}\n"
                "\\bibliographystyle{amsplain}\n"
                "\\bibliography{\\subfix{../../references_alpha},\\subfix{../../references_beta}}\n"
                "\\end{document}\n"
            ),
        )
        common.write_json(
            common.atom_sidecar_path(wrapper_path),
            {
                "kg_id": "KG-20260303-0099",
                "label": "backmatter-main",
                "atom_type": "tp-note",
                "parents": [],
                "source_path": str(source_file),
            },
        )

        spec = self.kg_root / "index_specs" / "wrapper.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: wrapper",
                    "roots: backmatter-main",
                    "include_types: tp-note",
                    "reference_closure: false",
                    "include_wrapper_fragments: true",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        out_dir = out_tex.parent
        alias_file = out_dir / "atoms" / "KG-20260303-0099.tex"
        self.assertTrue(alias_file.exists())
        payload = alias_file.read_text(encoding="utf-8")
        self.assertNotIn("\\documentclass", payload)
        self.assertIn("\\bibliographystyle{amsplain}", payload)
        self.assertIn((self.repo_root / "docs" / "references_alpha").as_posix(), payload)
        self.assertIn((self.repo_root / "docs" / "references_beta").as_posix(), payload)

    def test_build_index_rejects_deprecated_source_alias_keys(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0101",
            label="alias-source-atom",
            atom_type="tp-note",
            ext="tex",
            content="\\paragraph{Alias Source}\\label{kg:alias-source-atom}\n",
        )

        spec = self.kg_root / "index_specs" / "deprecated_alias_keys.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: deprecated_alias_keys",
                    "roots: alias-source-atom",
                    "include_types: tp-note",
                    "reference_closure: false",
                    "source_alias_mode: off",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_index.build_single_spec(self.kg_root, spec)

        spec.write_text(
            "\n".join(
                [
                    "name: deprecated_alias_keys",
                    "roots: alias-source-atom",
                    "include_types: tp-note",
                    "reference_closure: false",
                    "expose_source_aliases: true",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError):
            build_index.build_single_spec(self.kg_root, spec)

    def test_build_index_removes_legacy_source_aliases_dir(self) -> None:
        write_atom(
            self.kg_root,
            kg_id="KG-20260303-0102",
            label="legacy-dir-clean",
            atom_type="tp-note",
            ext="tex",
            content="\\paragraph{Legacy Dir}\\label{kg:legacy-dir-clean}\n",
        )

        spec = self.kg_root / "index_specs" / "legacy_dir_clean.idx"
        spec.write_text(
            "\n".join(
                [
                    "name: legacy_dir_clean",
                    "roots: legacy-dir-clean",
                    "include_types: tp-note",
                    "reference_closure: false",
                    "order: topo",
                ]
            ),
            encoding="utf-8",
        )

        out_dir = self.kg_root / "index_nodes" / "legacy_dir_clean"
        legacy_source_alias_dir = out_dir / "source_aliases"
        legacy_source_alias_dir.mkdir(parents=True, exist_ok=True)
        (legacy_source_alias_dir / "old_alias.tex").write_text("% old\n", encoding="utf-8")

        out_tex = build_index.build_single_spec(self.kg_root, spec)
        self.assertTrue(out_tex.exists())
        self.assertFalse(legacy_source_alias_dir.exists())
        self.assertTrue(build_index.atoms_dir_has_only_kg_aliases(out_dir / "atoms"))

    def test_compile_texinputs_env_does_not_include_source_aliases_dir(self) -> None:
        index_dir = self.kg_root / "index_nodes" / "sample"
        atoms_dir = index_dir / "atoms"
        source_alias_dir = index_dir / "source_aliases"
        atoms_dir.mkdir(parents=True, exist_ok=True)
        source_alias_dir.mkdir(parents=True, exist_ok=True)
        index_main = index_dir / "idx_sample_main.tex"
        index_main.write_text("% index\n", encoding="utf-8")

        env = kg_compile.build_texinputs_env(self.kg_root, [index_main], [])
        texinputs = env.get("TEXINPUTS", "")
        self.assertNotIn(source_alias_dir.resolve().as_posix(), texinputs)

    def test_repair_unbalanced_display_math_closes_before_blank_line(self) -> None:
        tex = "\\begin{remark}\n$$\na+b\n\n\\end{remark}\n"
        repaired, reason = build_index.repair_unbalanced_display_math(tex)
        self.assertIsNotNone(reason)
        self.assertIn("$$\na+b\n$$\n\n\\end{remark}\n", repaired)


if __name__ == "__main__":
    unittest.main()
