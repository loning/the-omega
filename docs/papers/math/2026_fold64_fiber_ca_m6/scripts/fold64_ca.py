
"""
fold64_ca.py

A phase-indexed local rewriting (radius-2) cellular automaton that computes

    (a + b) mod 64

for a,b in {0,...,63}, using only:
    - Unfold: pointwise digit addition on Fibonacci (Zeckendorf) tracks
    - Fold_64: local rewrite normalization + conditional subtract of 64

The CA is specified by a phase program of length P=90, and a set of
phase-indexed neighborhood->next-state tables, generated from all reachable
neighborhoods across all 64^2 input pairs.

State encoding (per cell):
    (digit, head, role, m4, m3, t)

digit in {-1,0,1,2,3}
head in {0..5} = NONE,E,G,L,BGE,BLT
role in {'ghost','d1','d2','mid','src'}
m4 = index mod 4 (0..3) for non-ghost, else 0
m3 = index mod 3 (0..2) for non-ghost, else 0
t  = 1 only at indices {2,6,10}, else 0

Neighborhood radius = 2.
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

# --- Fibonacci numbers F[0..12] ---
F = [0, 1, 1]
for k in range(3, 13):
    F.append(F[k-1] + F[k-2])

def zeck(n: int, K: int = 12) -> List[int]:
    """Zeckendorf digits d[1..K] for n>=0, using greedy, without F1."""
    d = [0] * (K + 1)
    rem = n
    k = K
    while rem > 0 and k >= 2:
        while k >= 2 and F[k] > rem:
            k -= 1
        if k < 2:
            break
        d[k] = 1
        rem -= F[k]
        k -= 2
    d[1] = 0
    return d

def val(d: List[int]) -> int:
    return sum(d[k] * F[k] for k in range(1, len(d)))

# --- static tags on indices -3..16 (to support radius-2 neighborhoods for 1..12) ---
L = 12
IDX_MIN = -3
IDX_MAX = L + 4  # 16
IDXS = list(range(IDX_MIN, IDX_MAX + 1))  # inclusive

T_MASK = {2, 6, 10}
ROLE_CODE = {"ghost": "G", "d1": "1", "d2": "2", "mid": "M", "src": "S"}
REV_ROLE_CODE = {v: k for k, v in ROLE_CODE.items()}

def role(i: int) -> str:
    if i < 1 or i > L:
        return "ghost"
    if i == 1:
        return "d1"
    if i == 2:
        return "d2"
    if i == L:
        return "src"
    return "mid"

def m4(i: int) -> int:
    return (i % 4) if role(i) != "ghost" else 0

def m3(i: int) -> int:
    return (i % 3) if role(i) != "ghost" else 0

def tbit(i: int) -> int:
    return 1 if (role(i) != "ghost" and i in T_MASK) else 0

# head symbols
NONE, E, G, Ls, BGE, BLT = range(6)

@dataclass(frozen=True)
class Cell:
    d: int
    h: int
    r: str
    m4: int
    m3: int
    t: int

def encode_cell(c: Cell) -> str:
    return f"{c.d}:{c.h}:{ROLE_CODE[c.r]}:{c.m4}:{c.m3}:{c.t}"

def decode_cell(s: str) -> Cell:
    d_str, h_str, r_str, m4_str, m3_str, t_str = s.split(":")
    return Cell(
        d=int(d_str),
        h=int(h_str),
        r=REV_ROLE_CODE[r_str],
        m4=int(m4_str),
        m3=int(m3_str),
        t=int(t_str),
    )

def neigh_key(cells: List[Cell]) -> str:
    return "|".join(encode_cell(c) for c in cells)

def cell_at(digits: Dict[int, int], heads: Dict[int, int], i: int) -> Cell:
    return Cell(
        d=digits.get(i, 0),
        h=heads.get(i, NONE),
        r=role(i),
        m4=m4(i),
        m3=m3(i),
        t=tbit(i),
    )

def init_digits_heads(a: int, b: int) -> Tuple[Dict[int, int], Dict[int, int]]:
    """Initialize digits as Unfold(zeck(a), zeck(b)), head empty."""
    A = zeck(a, L)
    B = zeck(b, L)
    digits = {i: 0 for i in IDXS}
    heads = {i: NONE for i in IDXS}
    for i in IDXS:
        if role(i) == "ghost":
            digits[i] = 0
        else:
            digits[i] = A[i] + B[i]
    return digits, heads

def load_tables(path: str) -> Tuple[int, List[Dict[str, str]]]:
    with open(path, "r") as f:
        obj = json.load(f)
    P = obj["P"]
    tables = obj["tables"]
    return P, tables

def step(digits: Dict[int, int], heads: Dict[int, int], p: int, tables: List[Dict[str, str]]) -> Tuple[Dict[int, int], Dict[int, int]]:
    """One CA step at phase p, using neighborhood->next-state table."""
    tbl = tables[p]
    new_digits = digits.copy()
    new_heads = heads.copy()

    for i in range(1, L + 1):
        neigh = [cell_at(digits, heads, j) for j in range(i - 2, i + 3)]
        k = neigh_key(neigh)
        out = tbl.get(k)
        if out is None:
            raise KeyError(f"Missing neighborhood at phase {p}: i={i}, key={k}")
        c = decode_cell(out)
        new_digits[i] = c.d
        new_heads[i] = c.h

    # enforce ghosts fixed
    for i in IDXS:
        if role(i) == "ghost":
            new_digits[i] = 0
            new_heads[i] = NONE
    return new_digits, new_heads

def run_add(a: int, b: int, tables_path: str) -> List[int]:
    P, tables = load_tables(tables_path)
    digits, heads = init_digits_heads(a, b)
    for p in range(P):
        digits, heads = step(digits, heads, p, tables)
    out = [0] * (L + 1)
    for k in range(1, L + 1):
        out[k] = digits[k]
    return out

if __name__ == "__main__":
    # quick sanity check
    import sys
    from pathlib import Path
    if len(sys.argv) < 2:
        repo_dir = Path(__file__).resolve().parent.parent
        default_rules = repo_dir / "artifacts" / "fold64_ca_rules_phase90.json"
        print("Usage: python fold64_ca.py <rules_json_path>")
        print(f"Default: {default_rules}")
        sys.exit(0)
    rules_path = sys.argv[1]

    # verify all 64^2 pairs
    for a in range(64):
        for b in range(64):
            d = run_add(a, b, rules_path)
            if val(d) != (a + b) % 64:
                raise RuntimeError(f"Mismatch: a={a}, b={b}, got={val(d)}, want={(a+b)%64}, d={d}")
    print("OK: verified all 64^2 pairs.")
