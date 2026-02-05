#!/usr/bin/env python3
"""
Shared pylatex helpers for emitting LaTeX fragments.

Design goal:
  - scripts output *fragments* (not standalone documents), intended to be \\input into the paper.
  - output is deterministic and auditable (explicit strings + pylatex object dumps).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

from pylatex import Figure, NoEscape, Tabular


Latex = Union[str, NoEscape]


def write_tex_fragment(out_path: Path, content: Union[str, "Tabular", "Figure"], comment: Optional[str] = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = ""
    if comment:
        c = comment.strip()
        prefix = f"% {c}\n"
    if isinstance(content, str):
        out_path.write_text(prefix + content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
        return
    out_path.write_text(prefix + content.dumps() + "\n", encoding="utf-8")


def booktabs_tabular(
    col_spec: str,
    header: Sequence[Latex],
    rows: Iterable[Sequence[Latex]],
) -> Tabular:
    """
    Create a tabular environment with \\toprule/\\midrule/\\bottomrule.
    The paper loads booktabs, so these commands are available in the main document.
    """
    tab = Tabular(col_spec)
    tab.append(NoEscape(r"\toprule"))
    tab.add_row(list(header))
    tab.append(NoEscape(r"\midrule"))
    for r in rows:
        tab.add_row(list(r))
    tab.append(NoEscape(r"\bottomrule"))
    return tab


def figure_includegraphics(
    rel_graphics_path: str,
    caption_tex: str,
    label: str,
    width_tex: str = r"0.90\linewidth",
    position: str = "H",
) -> Figure:
    fig = Figure(position=position)
    fig.append(NoEscape(r"\centering"))
    fig.append(NoEscape(rf"\includegraphics[width={width_tex}]{{{rel_graphics_path}}}"))
    fig.add_caption(NoEscape(caption_tex))
    # NOTE: labels are identifiers; do NOT escape underscores.
    fig.append(NoEscape(rf"\label{{{label}}}"))
    return fig

