#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate LaTeX fragments using PyLaTeX (no manual string concatenation)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Sequence

from pylatex import NoEscape, Tabular


def write_tabular_fragment(
    path: Path,
    column_spec: str,
    header: Sequence[str],
    rows: Iterable[Sequence[Any]],
    booktabs: bool = True,
) -> None:
    tab = Tabular(column_spec)

    if booktabs:
        tab.add_hline()
    tab.add_row([NoEscape(h) for h in header])
    if booktabs:
        tab.add_hline()

    for r in rows:
        cells: List[str] = []
        for x in r:
            dumps = getattr(x, "dumps", None)
            if callable(dumps):
                cells.append(dumps())
            else:
                cells.append(str(x))
        tab.add_row([NoEscape(c) for c in cells])

    if booktabs:
        tab.add_hline()

    tex = tab.dumps() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tex, encoding="utf-8")


def write_lines_as_fragment(path: Path, lines: List[str]) -> None:
    # In PyLaTeX, NoEscape behaves as a string-like wrapper; use str(...) for portability.
    content = "\n".join([str(NoEscape(x)) for x in lines]) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

