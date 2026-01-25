
"""
generate_fold64_ca_rules.py

Generate the phase-indexed neighborhood->next-state rule tables for the
Fold_64 local rewriting CA (m=6). The resulting JSON file is sufficient
to simulate the CA exactly for all input pairs a,b in {0,...,63}.

Output:
  fold64_ca_rules_phase90.json
"""

from __future__ import annotations
import json
from collections import defaultdict
from typing import Dict, Tuple, List
from pathlib import Path
import time

# --- Fibonacci numbers F[0..12] ---
F = [0,1,1]
for k in range(3,13):
    F.append(F[k-1]+F[k-2])

def zeck(n: int, K: int = 12) -> List[int]:
    d = [0]*(K+1)
    rem = n
    k = K
    while rem>0 and k>=2:
        while k>=2 and F[k] > rem:
            k -= 1
        if k < 2:
            break
        d[k] = 1
        rem -= F[k]
        k -= 2
    d[1] = 0
    return d

# --- CA static layout (indices -3..16, active cells 1..12) ---
L = 12
IDX_MIN = -3
IDX_MAX = L + 4
IDXS = list(range(IDX_MIN, IDX_MAX + 1))

T_MASK = {2,6,10}

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

ROLE_CODE = {"ghost": "G", "d1": "1", "d2": "2", "mid": "M", "src": "S"}

# head symbols
NONE, E, G, Ls, BGE, BLT = range(6)

# schedule parameters (P=90)
NORM1_TICKS = 3
NORM2_TICKS = 2
NEGFIX_TICKS = 3
COMPARE_STEPS = L-1
BACK_STEPS = L-1
ALIGN_STEPS = 4

p_norm1_end = 9*NORM1_TICKS      # 27
p_inject = p_norm1_end           # 27
p_compare_start = p_inject+1     # 28
p_compare_end = p_compare_start + COMPARE_STEPS  # 39
p_back_start = p_compare_end     # 39
p_back_end = p_back_start + BACK_STEPS           # 50
p_negfix_start = p_back_end                        # 50
p_negfix_end = p_negfix_start + 6*NEGFIX_TICKS     # 68
p_align_start = p_negfix_end                       # 68
p_norm2_start = p_align_start + ALIGN_STEPS        # 72
P = p_norm2_start + 9*NORM2_TICKS                  # 90

def update_symbol(sym: int, x: int, t: int) -> int:
    if sym == E:
        if x > t:
            return G
        if x < t:
            return Ls
        return E
    if sym in (G, Ls):
        return sym
    return sym

def init_config(a: int, b: int) -> Tuple[Dict[int,int], Dict[int,int]]:
    A = zeck(a, L)
    B = zeck(b, L)
    digits = {i:0 for i in IDXS}
    head = {i:NONE for i in IDXS}
    for i in IDXS:
        if role(i) == "ghost":
            digits[i] = 0
        else:
            digits[i] = A[i] + B[i]
    return digits, head

def freeze(new_digits: Dict[int,int], new_head: Dict[int,int]):
    for i in IDXS:
        if role(i) == "ghost":
            new_digits[i] = 0
            new_head[i] = NONE

def ca_step(digits: Dict[int,int], head: Dict[int,int], p: int) -> Tuple[Dict[int,int], Dict[int,int]]:
    new_digits = digits.copy()
    new_head = {i:NONE for i in IDXS}

    # Norm stages
    if p < p_norm1_end or (p >= p_norm2_start and p < P):
        sub = p % 9
        if sub <= 3:
            color = sub
            A = {i: (1 if role(i)!="ghost" and m4(i)==color and digits[i]>=2 else 0) for i in IDXS}
            for i in IDXS:
                if role(i) == "ghost":
                    continue
                new_digits[i] = digits[i] - 2*A.get(i,0) + A.get(i-1,0) + A.get(i+2,0)
            freeze(new_digits, new_head)
            return new_digits, new_head
        if 4 <= sub <= 7:
            color = sub - 4
            B = {i: (1 if role(i)!="ghost" and m4(i)==color and digits[i]>=1 and digits.get(i-1,0)>=1 else 0) for i in IDXS}
            for i in IDXS:
                if role(i) == "ghost":
                    continue
                new_digits[i] = digits[i] - B.get(i,0) - B.get(i+1,0) + B.get(i-1,0)
            freeze(new_digits, new_head)
            return new_digits, new_head
        # sub==8 absorb
        new_digits[2] = digits.get(2,0) + digits.get(1,0)
        new_digits[1] = 0
        freeze(new_digits, new_head)
        return new_digits, new_head

    # Align stage
    if p_align_start <= p < p_norm2_start:
        freeze(new_digits, new_head)
        return new_digits, new_head

    # Inject
    if p == p_inject:
        new_head[L] = E
        freeze(new_digits, new_head)
        return new_digits, new_head

    # Compare
    if p_compare_start <= p < p_compare_end:
        for i in IDXS:
            if role(i) == "ghost":
                continue
            sym = head.get(i+1, NONE)
            if sym in (E,G,Ls):
                x = 1 if digits.get(i+1,0) > 0 else 0
                new_head[i] = update_symbol(sym, x, tbit(i+1))
        freeze(new_digits, new_head)
        return new_digits, new_head

    # Back
    if p_back_start <= p < p_back_end:
        for i in IDXS:
            if role(i) != "ghost" and head.get(i,NONE)==BGE and tbit(i)==1:
                new_digits[i] = digits[i] - 1
        for i in IDXS:
            if role(i) == "ghost":
                continue
            sym = head.get(i-1, NONE)
            if sym in (BGE, BLT):
                new_head[i] = sym
            elif sym in (E,G,Ls):
                new_head[i] = BLT if sym==Ls else BGE
        freeze(new_digits, new_head)
        return new_digits, new_head

    # NegFix
    if p_negfix_start <= p < p_negfix_end:
        sub = (p - p_negfix_start) % 6
        if sub <= 2:
            color = sub
            delta = {i:0 for i in IDXS}
            for i in IDXS:
                if role(i)=="ghost" or m3(i)!=color:
                    continue
                if digits[i] < 0 and digits.get(i+1,0) > 0:
                    delta[i]   += 1
                    delta[i+1] -= 1
                    delta[i-1] += 1
                if digits[i] < 0 and digits.get(i+2,0) > 0:
                    delta[i]   += 1
                    delta[i+1] += 1
                    delta[i+2] -= 1
                if digits[i] < 0 and digits.get(i+1,0) == 0:
                    delta[i]   += 1
                    delta[i+1] -= 1
                    delta[i-1] += 1
            for i in IDXS:
                if role(i) != "ghost":
                    new_digits[i] = digits[i] + delta[i]
            freeze(new_digits, new_head)
            return new_digits, new_head
        # borrow
        color = sub - 3
        delta = {i:0 for i in IDXS}
        for k in IDXS:
            if role(k)=="ghost" or m3(k)!=color:
                continue
            if digits[k] > 0 and digits.get(k-2,0) < 0:
                delta[k]   -= 1
                delta[k-1] += 1
                delta[k-2] += 1
        for i in IDXS:
            if role(i) != "ghost":
                new_digits[i] = digits[i] + delta[i]
        if sub == 5:
            new_digits[2] = new_digits.get(2,0) + new_digits.get(1,0)
            new_digits[1] = 0
        freeze(new_digits, new_head)
        return new_digits, new_head

    freeze(new_digits, new_head)
    return new_digits, new_head

def cell_state(digits: Dict[int,int], head: Dict[int,int], i: int) -> Tuple[int,int,str,int,int,int]:
    return (digits.get(i,0), head.get(i,NONE), role(i), m4(i), m3(i), tbit(i))

def encode_state(st: Tuple[int,int,str,int,int,int]) -> str:
    d,h,r,m4v,m3v,t = st
    return f"{d}:{h}:{ROLE_CODE[r]}:{m4v}:{m3v}:{t}"

def encode_neigh(neigh: Tuple[Tuple[int,int,str,int,int,int], ...]) -> str:
    return "|".join(encode_state(s) for s in neigh)

def main():
    rules = [dict() for _ in range(P)]
    t0 = time.time()
    for a in range(64):
        for b in range(64):
            digits, head = init_config(a,b)
            for p in range(P):
                next_digits, next_head = ca_step(digits, head, p)
                for i in range(1, L+1):
                    neigh = tuple(cell_state(digits, head, j) for j in range(i-2, i+3))
                    nxt = cell_state(next_digits, next_head, i)
                    key = encode_neigh(neigh)
                    val = encode_state(nxt)
                    prev = rules[p].get(key)
                    if prev is None:
                        rules[p][key] = val
                    elif prev != val:
                        raise RuntimeError(f"Conflict at phase {p}")
                digits, head = next_digits, next_head
        # progress (ensure periodic output for long runs)
        if (a + 1) % 1 == 0:
            dt = time.time() - t0
            rate = (a + 1) / max(dt, 1e-9)
            eta = (64 - (a + 1)) / max(rate, 1e-9)
            print(f"[progress] a={a+1}/64 elapsed={dt:.1f}s eta={eta:.1f}s", flush=True)

    out = {"P": P, "tables": rules}
    repo_dir = Path(__file__).resolve().parent.parent
    out_dir = repo_dir / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "fold64_ca_rules_phase90.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
