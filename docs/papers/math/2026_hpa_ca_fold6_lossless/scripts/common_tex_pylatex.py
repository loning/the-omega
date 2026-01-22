#!/usr/bin/env python3
"""Generate LaTeX fragments using PyLaTeX (no manual string concatenation).

We intentionally generate *fragments* (e.g., tabular environments) that can be
\\input{} into the paper. PyLaTeX still renders to a string at the end, but the
structure is assembled via objects rather than handcrafted TeX strings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Sequence

from pylatex import Command, NoEscape, Tabular


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
    # Use a Tabular-less container by joining NoEscape dumps.
    # Note: callers should pass complete TeX lines; we avoid building TeX by concatenation at call sites.
    content = "\n".join([NoEscape(x).dumps() for x in lines]) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

