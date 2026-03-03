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
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import _kg_common as common  # noqa: E402
import kg_build_index as build_index  # noqa: E402
import kg_compile as kg_compile  # noqa: E402
import kg_emit_llm_tasks as emit_tasks  # noqa: E402
import kg_ingest_atoms as ingest_atoms  # noqa: E402
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

    def test_emit_task_helpers(self) -> None:
        self.assertEqual(emit_tasks.suggested_type("deleted", "a.tex"), "tp-errata")
        self.assertEqual(emit_tasks.suggested_type("modified", "x.py"), "tp-method")
        self.assertEqual(
            emit_tasks.suggested_type("modified", "sections/generated/z.tex"),
            "tp-artifact",
        )

        labels = ["fold-map", "scan-axiom", "something-else"]
        candidates = emit_tasks.find_candidate_labels("fold/map_script.py", labels)
        self.assertIn("fold-map", candidates)

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
        self.assertIn("\\paragraph{Proof.}", content)
        self.assertNotIn("\\begin{proof}", content)

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
        self.assertIn("\\paragraph{Proof.}", content)
        self.assertIn("\\begin{remark}", content)
        self.assertIn("\\end{remark}", content)
        self.assertNotIn("\\end{proof}", content)

    def test_ingest_skips_orphan_proof_atom_without_parent(self) -> None:
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
        self.assertEqual(len(atom_files), 0)

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
        self.assertIn("Skipped Root TeX Atoms", content)
        self.assertIn("rootdoc", content)
        manifest = json.loads((out_tex.parent / "manifest.json").read_text(encoding="utf-8"))
        self.assertIn("selection_fingerprint", manifest)

        mtime_before = out_tex.stat().st_mtime_ns
        time.sleep(1.1)
        out_tex_2 = build_index.build_single_spec(self.kg_root, spec)
        mtime_after = out_tex_2.stat().st_mtime_ns
        self.assertEqual(out_tex_2, out_tex)
        self.assertEqual(mtime_before, mtime_after)

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
        self.assertIn("\\hfuzz=100pt", template)


if __name__ == "__main__":
    unittest.main()
