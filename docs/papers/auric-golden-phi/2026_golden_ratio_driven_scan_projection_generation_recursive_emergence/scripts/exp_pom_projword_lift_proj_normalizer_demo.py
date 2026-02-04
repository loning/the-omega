#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Executable demo: projection-word rewriting with E[m], LIFT(G), PROJ(u).

This is a small, auditable witness for the extended PW rewriting fragment
discussed in the paper (PW 2-category + rewrite certificates).

Token convention (matches other PW normalizers in this repo):
- Tokens are written left-to-right in categorical composition order.
  That is, the rightmost token acts first.

We support a minimal typed fragment with tokens:
- PZ                 : normalization projection gate P_Z (idempotent)
- E[m] (or Em)       : conditional expectation tower gate E_m
- LIFT[Cn]           : a finite abelian lift; here we model cyclic group C_n
- PROJ[u]            : readout projection with temperature parameter u

Rewrite rules (oriented for normalization):
  (RZ)     PZ ∘ PZ              -> PZ
  (RE)     E[m1] ∘ E[m2]        -> E[min(m1,m2)]   (tower)
  (RBC)    E[m] ∘ LIFT[G]       -> LIFT[G] ∘ E[m]  (Beck–Chevalley style swap)
  (RA)     PROJ[u] ∘ LIFT[Cn]   -> PROD( PROJ[u,chi0] ⊗ ... ⊗ PROJ[u,chi_{n-1}] )
           (Artin/character factorization as a 2-morphism witness)

We treat PROD(...) as an atomic "parallel/tensor bundle" token in this demo.

Outputs:
  - artifacts/export/pom_projword_lift_proj_normalizer_demo.json
  - sections/generated/tab_pom_projword_lift_proj_normalizer_demo.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from common_paths import export_dir, generated_dir


@dataclass(frozen=True)
class Tok:
    kind: str  # PZ, E, LIFT, PROJ, PROD
    arg: str | None = None

    def render(self) -> str:
        if self.arg is None:
            return self.kind
        return f"{self.kind}[{self.arg}]"


_E_RE = re.compile(r"^E\[?(\d+)\]?$")
_LIFT_RE = re.compile(r"^LIFT\[(.+)\]$")
_PROJ_RE = re.compile(r"^PROJ\[(.+)\]$")
_PROD_RE = re.compile(r"^PROD\[(.+)\]$")


def parse_word(s: str) -> List[Tok]:
    parts = [p.strip() for p in s.split() if p.strip()]
    out: List[Tok] = []
    for p in parts:
        if p == "PZ":
            out.append(Tok("PZ"))
            continue
        m = _E_RE.match(p)
        if m:
            out.append(Tok("E", m.group(1)))
            continue
        m = _LIFT_RE.match(p)
        if m:
            out.append(Tok("LIFT", m.group(1)))
            continue
        m = _PROJ_RE.match(p)
        if m:
            out.append(Tok("PROJ", m.group(1)))
            continue
        m = _PROD_RE.match(p)
        if m:
            out.append(Tok("PROD", m.group(1)))
            continue
        raise SystemExit(f"Bad token: {p}. Use PZ, E[m], LIFT[...], PROJ[...].")
    return out


def word_to_str(w: List[Tok]) -> str:
    return " ".join(t.render() for t in w)


def _lift_chars(group: str) -> List[str]:
    # Minimal model: only cyclic groups Cn.
    if not group.startswith("C"):
        raise ValueError(f"Only cyclic groups Cn supported in this demo, got {group!r}")
    n = int(group[1:])
    if n <= 0:
        raise ValueError("Cyclic group order must be positive")
    return [f"chi{i}" for i in range(n)]


def rewrite_once(w: List[Tok]) -> Tuple[List[Tok], bool, str]:
    # (RZ) local contraction: PZ PZ -> PZ
    for i in range(len(w) - 1):
        if w[i].kind == "PZ" and w[i + 1].kind == "PZ":
            return w[:i] + [Tok("PZ")] + w[i + 2 :], True, "RZ"

    # (RE) tower: E[m1] E[m2] -> E[min(m1,m2)]
    for i in range(len(w) - 1):
        if w[i].kind == "E" and w[i + 1].kind == "E":
            m1 = int(w[i].arg or "0")
            m2 = int(w[i + 1].arg or "0")
            return w[:i] + [Tok("E", str(min(m1, m2)))] + w[i + 2 :], True, "RE"

    # (RBC) swap: E[m] LIFT[G] -> LIFT[G] E[m]
    for i in range(len(w) - 1):
        if w[i].kind == "E" and w[i + 1].kind == "LIFT":
            return w[:i] + [w[i + 1], w[i]] + w[i + 2 :], True, "RBC"

    # (RA) Artin/character factorization: PROJ[u] LIFT[Cn] -> PROD[...]
    for i in range(len(w) - 1):
        if w[i].kind == "PROJ" and w[i + 1].kind == "LIFT":
            u = w[i].arg or "u"
            group = w[i + 1].arg or "C1"
            chis = _lift_chars(group)
            parts = [f"PROJ[{u},{chi}]" for chi in chis]
            # Keep ASCII-only in artifacts/tex for portability.
            prod = Tok("PROD", " OTIMES ".join(parts))
            return w[:i] + [prod] + w[i + 2 :], True, "RA"

    return w, False, ""


def normalize(w: List[Tok], step_cap: int = 100_000) -> Tuple[List[Tok], List[str]]:
    cur = list(w)
    trace: List[str] = []
    for _ in range(step_cap):
        cur, changed, rule = rewrite_once(cur)
        if not changed:
            return cur, trace
        trace.append(rule)
    raise RuntimeError("rewrite did not terminate within cap (unexpected)")


def tex_escape_tt(s: str) -> str:
    # Minimal escaping for \texttt
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("%", "\\%")
        .replace("&", "\\&")
        .replace("#", "\\#")
        .replace("^", "\\^{}")
        .replace("~", "\\~{}")
    )


def write_table_tex(path: Path, rows: List[dict]) -> None:
    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Executable demo of an extended projection-word normal form with "
        "$P_Z$, $E_m$, $\\mathrm{LIFT}_G$, and $\\mathrm{PROJ}_u$ rewrite certificates "
        "(idempotence, tower, Beck--Chevalley swap, Artin/character factorization).}"
    )
    lines.append("\\label{tab:pom_projword_lift_proj_normalizer_demo}")
    lines.append("\\begin{tabular}{l l r}")
    lines.append("\\toprule")
    lines.append("input word & normal form & \\#rewrite steps\\\\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(f"\\texttt{{{r['input_tex']}}} & \\texttt{{{r['nf_tex']}}} & {r['steps']}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


DEFAULT_WORDS = [
    "PZ PZ E5 E12 PZ",
    "E7 LIFT[C5] E3",
    "PROJ[u] LIFT[C3] E10 E2",
    "PZ E8 PROJ[u] LIFT[C4] PZ E1",
    "E9 E4 PROJ[u] LIFT[C2] LIFT[C2]",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo PW rewriting with E/LIFT/PROJ (normal form witness).")
    parser.add_argument(
        "--words",
        type=str,
        default="|".join(DEFAULT_WORDS),
        help="Pipe-separated list of space-separated token words.",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "pom_projword_lift_proj_normalizer_demo.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_pom_projword_lift_proj_normalizer_demo.tex"),
    )
    args = parser.parse_args()

    word_strs = [w.strip() for w in str(args.words).split("|") if w.strip()]
    rows: List[dict] = []
    for ws in word_strs:
        w = parse_word(ws)
        nf, trace = normalize(w)
        rows.append(
            {
                "input": word_to_str(w),
                "normal_form": word_to_str(nf),
                "rewrite_trace": trace,
                "steps": len(trace),
                "input_tex": tex_escape_tt(word_to_str(w)),
                "nf_tex": tex_escape_tt(word_to_str(nf)),
            }
        )

    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps({"rows": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[pw-lift-proj-demo] wrote {jout}", flush=True)

    tout = Path(args.tex_out)
    write_table_tex(tout, rows)
    print(f"[pw-lift-proj-demo] wrote {tout}", flush=True)


if __name__ == "__main__":
    main()

