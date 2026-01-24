#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observer Turing Machine (OTM) reference interpreter.

This is a small, auditable reference implementation for the paper section:
    - Observer TM: irreversible appearance + protocol-layer reversible embedding.

Design goals
------------
- Pure Python, no external dependencies.
- Deterministic branching + deterministic commit (beam truncation).
- Optional reversible TM-step embedding via a history stack (Bennett-style).
- Optional coupling to the Zeckendorf uplift protocol U/D steps (m, y, t, tr, E).

Notes
-----
1) This script is a *reference* interpreter. It is intentionally explicit and
   favors auditability over speed.
2) The "branching" supported here is through *non-deterministic transition tables*
   (multiple actions for the same (state, symbol)). This lets the observer maintain
   a branch set and then commit deterministically under an energy-induced beam width.
3) The Zeckendorf uplift coupling is implemented for general m using the existing
   helper module `common_zeckendorf_uplift.py`.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple

from common_zeckendorf_uplift import (
    fold_f_m,
    micro_N_from_macro_and_tail,
    tail_inverse_step_candidates,
    tail_length,
    tail_shift_word,
)


Move = Literal["L", "R", "S"]


def _now_s() -> float:
    return float(time.time())


def _progress(msg: str, last_print_s: List[float], interval_s: float = 20.0) -> None:
    """Print progress at least every interval_s seconds."""
    t = _now_s()
    if (t - last_print_s[0]) >= interval_s:
        print(msg, flush=True)
        last_print_s[0] = t


def _bitstring_to_int_low_to_high(bits: str) -> int:
    """Parse bits b1..bL (as a string like '0101') into an int with bit0=b1 (low-to-high)."""
    b = bits.strip()
    if b == "":
        return 0
    if any(ch not in "01" for ch in b):
        raise ValueError(f"invalid bitstring: {bits!r}")
    out = 0
    for i, ch in enumerate(b):
        if ch == "1":
            out |= 1 << i
    return int(out)


def _int_to_bitstring_low_to_high(x: int, width: int) -> str:
    return "".join("1" if (x >> i) & 1 else "0" for i in range(width))


@dataclass(frozen=True)
class TMAction:
    next_state: str
    write: str
    move: Move


@dataclass(frozen=True)
class TMProgram:
    blank: str
    start_state: str
    halt_states: Tuple[str, ...]
    transitions: Dict[Tuple[str, str], Tuple[TMAction, ...]]

    @staticmethod
    def from_json(path: Path) -> "TMProgram":
        obj = json.loads(path.read_text(encoding="utf-8"))
        blank = str(obj.get("blank", "_"))
        start = str(obj["start"])
        halt = tuple(str(s) for s in obj.get("halt", []))
        raw = obj.get("transitions", {})

        transitions: Dict[Tuple[str, str], Tuple[TMAction, ...]] = {}
        for state, sym_map in raw.items():
            for sym, acts in sym_map.items():
                if not isinstance(acts, list) or len(acts) == 0:
                    raise ValueError(f"transitions[{state}][{sym}] must be a non-empty list")
                parsed: List[TMAction] = []
                for a in acts:
                    if not isinstance(a, dict):
                        raise ValueError(f"transition action must be an object, got: {type(a)}")
                    move = str(a.get("move", "S")).upper()
                    if move not in ("L", "R", "S"):
                        raise ValueError(f"invalid move: {move!r} (must be L/R/S)")
                    parsed.append(
                        TMAction(
                            next_state=str(a["next"]),
                            write=str(a["write"]),
                            move=move,  # type: ignore[assignment]
                        )
                    )
                transitions[(str(state), str(sym))] = tuple(parsed)

        return TMProgram(blank=blank, start_state=start, halt_states=halt, transitions=transitions)

    def actions(self, state: str, sym: str) -> Tuple[TMAction, ...]:
        return self.transitions.get((state, sym), tuple())

    def is_halt(self, state: str) -> bool:
        return state in self.halt_states


class SparseTape:
    """A sparse representation of a bi-infinite tape tp: Z -> Gamma."""

    def __init__(self, blank: str) -> None:
        self.blank = blank
        self.cells: Dict[int, str] = {}

    def read(self, pos: int) -> str:
        return self.cells.get(int(pos), self.blank)

    def write(self, pos: int, sym: str) -> None:
        p = int(pos)
        if sym == self.blank:
            self.cells.pop(p, None)
        else:
            self.cells[p] = str(sym)

    def clone(self) -> "SparseTape":
        t = SparseTape(blank=self.blank)
        t.cells = dict(self.cells)
        return t

    def read_from_zero_until_blank(self, limit: int = 1_000_000) -> str:
        out: List[str] = []
        for i in range(limit):
            s = self.read(i)
            if s == self.blank:
                break
            out.append(s)
        return "".join(out)


@dataclass
class HistoryRecord:
    state: str
    head_pos: int
    old_sym: str
    move: Move


@dataclass
class Branch:
    # TM-facing state
    q: str
    hp: int
    tape: SparseTape

    # Protocol-facing registers (optional coupling)
    m: int
    y_w: int  # packed low-to-high bits, length m
    L: int  # tail length
    t: int  # packed low-to-high bits, length L
    tr: str  # protocol trace bits
    E: str  # energy tape bits

    # Optional Bennett history for TM-step reversible embedding
    hist: List[HistoryRecord]

    def clone(self) -> "Branch":
        return Branch(
            q=str(self.q),
            hp=int(self.hp),
            tape=self.tape.clone(),
            m=int(self.m),
            y_w=int(self.y_w),
            L=int(self.L),
            t=int(self.t),
            tr=str(self.tr),
            E=str(self.E),
            hist=list(self.hist),
        )


def ok_Clo(m: int, y_w: int, t: int) -> bool:
    """A concrete, auditable Clo-guard for (y,t) in the Zeckendorf folding instance."""
    N = int(micro_N_from_macro_and_tail(int(y_w), int(t), m=int(m)))
    if not (0 <= N < (1 << int(m))):
        return False
    if int(fold_f_m(N, m=int(m))) != int(y_w):
        return False
    return True


def _build_code_map_for_y(m: int, y_w: int) -> Tuple[Dict[int, str], Dict[str, int], int]:
    """Code_y: enumerate the fiber Fold^{-1}(y) by increasing N and encode as fixed-width binary."""
    pre: List[int] = []
    for N in range(1 << m):
        if int(fold_f_m(N, m=m)) == int(y_w):
            pre.append(int(N))
    pre.sort()
    s = len(pre)
    if s <= 0:
        raise ValueError("empty fiber for given y")
    k = int(math.ceil(math.log2(float(s))))
    code: Dict[int, str] = {}
    inv: Dict[str, int] = {}
    for idx, N in enumerate(pre):
        c = format(idx, f"0{k}b") if k > 0 else ""
        code[int(N)] = c
        inv[c] = int(N)
    return code, inv, k


def _pop_last_bit(bits: str) -> Tuple[str, int]:
    if bits == "":
        raise ValueError("cannot pop from empty bitstring")
    b = int(bits[-1])
    return bits[:-1], b


def _pop_suffix(bits: str, k: int) -> Tuple[str, str]:
    if k < 0:
        raise ValueError("k must be nonnegative")
    if k == 0:
        return bits, ""
    if len(bits) < k:
        raise ValueError("not enough bits to pop suffix")
    return bits[:-k], bits[-k:]


def U_step(branch: Branch) -> None:
    """Apply one protocol unfold step U to (y,t,tr,E)."""
    if branch.E == "":
        raise ValueError("E empty, cannot unfold")
    E_minus, b = _pop_last_bit(branch.E)
    cands = tail_inverse_step_candidates(branch.t, L=branch.L)
    good: List[int] = []
    for tp in cands:
        if ok_Clo(branch.m, branch.y_w, tp):
            good.append(int(tp))
    good.sort()
    if len(good) <= 0:
        raise ValueError("no admissible Tail^{-1} candidates")
    idx = int(b) if len(good) >= 2 else 0
    if idx >= len(good):
        raise ValueError("branch label b selects a non-existent candidate")
    tp = int(good[idx])
    Np = int(micro_N_from_macro_and_tail(branch.y_w, tp, m=branch.m))
    code_map, _, _k = _build_code_map_for_y(branch.m, branch.y_w)
    if Np not in code_map:
        raise ValueError("reconstructed N not in fiber (unexpected)")
    c = code_map[Np]
    branch.t = tp
    branch.tr = branch.tr + str(b)
    branch.E = E_minus + c


def D_step(branch: Branch) -> None:
    """Apply one protocol fold step D to (y,t,tr,E), inverse of U_step on its image."""
    if branch.tr == "":
        raise ValueError("tr empty, cannot fold")
    b = int(branch.tr[-1])
    tr_prev = branch.tr[:-1]
    code_map, inv_code_map, k = _build_code_map_for_y(branch.m, branch.y_w)
    E_minus, c = _pop_suffix(branch.E, k=k)
    if c not in inv_code_map:
        raise ValueError("unknown code suffix, cannot decode")
    N_ip1 = int(inv_code_map[c])
    # Roll back tail by Tail(t') = t, i.e., t = shift(t')
    t_prev = int(tail_shift_word(branch.t))
    if not ok_Clo(branch.m, branch.y_w, branch.t):
        raise ValueError("current (y,t) violates Clo guard, cannot fold")
    # Optional audit: ensure decoded N matches current tail+macro.
    N_check = int(micro_N_from_macro_and_tail(branch.y_w, branch.t, m=branch.m))
    if N_check != N_ip1:
        raise ValueError("decoded N does not match (y,t) reconstruction")
    branch.t = t_prev
    branch.tr = tr_prev
    branch.E = E_minus + str(b)


def tm_step(branch: Branch, program: TMProgram, reversible: bool) -> List[Branch]:
    """Execute one TM step. Returns list of next branches (can be >1 for non-determinism)."""
    if program.is_halt(branch.q):
        return [branch]
    a = branch.tape.read(branch.hp)
    actions = program.actions(branch.q, a)
    if len(actions) == 0:
        # Undefined transition: treat as halt (external convention).
        return [branch]

    out: List[Branch] = []
    for act in actions:
        nb = branch.clone()
        old_sym = nb.tape.read(nb.hp)
        if reversible:
            nb.hist.append(HistoryRecord(state=nb.q, head_pos=nb.hp, old_sym=old_sym, move=act.move))
        nb.tape.write(nb.hp, act.write)
        if act.move == "L":
            nb.hp -= 1
        elif act.move == "R":
            nb.hp += 1
        nb.q = act.next_state
        out.append(nb)
    return out


def commit(branches: Sequence[Branch]) -> List[Branch]:
    """Deterministic commit using a paper-consistent score tuple."""
    if len(branches) <= 1:
        return list(branches)
    # Score_y(t,tr) := (Rec_m(y,t), |tr|, tr, t), extended with TM state as a tiebreaker.
    scored: List[Tuple[Tuple[int, int, str, int, str], Branch]] = []
    for b in branches:
        N = int(micro_N_from_macro_and_tail(b.y_w, b.t, m=b.m))
        key = (int(N), int(len(b.tr)), str(b.tr), int(b.t), str(b.q))
        scored.append((key, b))
    scored.sort(key=lambda x: x[0])
    # Beam width per-branch depends on its E length.
    # For a branch set, we take the *minimum* available beam among branches (audit-friendly).
    beam = min((1 << len(b.E) for b in branches), default=1)
    return [b for (_k, b) in scored[:beam]]


def run(
    program: TMProgram,
    branch0: Branch,
    max_steps: int,
    reversible: bool,
    coupled_every: int,
    do_commit: bool,
    last_print_s: List[float],
) -> List[Branch]:
    branches: List[Branch] = [branch0]
    for step in range(max_steps):
        _progress(f"[observer_tm_ref] step={step} branches={len(branches)}", last_print_s=last_print_s)

        next_branches: List[Branch] = []
        for br in branches:
            # Optional Clo guard: if violated, drop branch (observer branch semantics).
            if not ok_Clo(br.m, br.y_w, br.t):
                continue
            # Optional coupling to protocol U-step every k TM steps.
            if coupled_every > 0 and (step % coupled_every == 0) and step > 0:
                try:
                    U_step(br)
                except Exception:
                    # Coupled mode: invalid unfold kills this branch.
                    continue
            next_branches.extend(tm_step(br, program=program, reversible=reversible))

        branches = next_branches
        if do_commit:
            branches = commit(branches)

        # Global halting: if all branches are in halt states, stop.
        if all(program.is_halt(b.q) for b in branches) or len(branches) == 0:
            break
    return branches


def _init_branch(
    program: TMProgram,
    input_bits: str,
    m: int,
    y_bits_low_to_high: str,
    t0_bits_low_to_high: str,
    E0: str,
) -> Branch:
    if any(ch not in "01" for ch in input_bits):
        raise ValueError("input must be a bitstring of 0/1")
    if any(ch not in "01" for ch in E0):
        raise ValueError("E0 must be a bitstring of 0/1")
    y_w = _bitstring_to_int_low_to_high(y_bits_low_to_high)
    L = int(tail_length(m))
    if t0_bits_low_to_high == "":
        t0 = 0
    else:
        t0 = _bitstring_to_int_low_to_high(t0_bits_low_to_high)
    if t0 < 0 or t0 >= (1 << L):
        raise ValueError(f"t0 out of range for L={L}")
    if not ok_Clo(m, y_w, t0):
        raise ValueError("initial (y,t0) violates Clo guard")

    tape = SparseTape(blank=program.blank)
    for i, ch in enumerate(input_bits):
        tape.write(i, ch)
    tape.write(len(input_bits), program.blank)

    return Branch(
        q=program.start_state,
        hp=0,
        tape=tape,
        m=int(m),
        y_w=int(y_w),
        L=int(L),
        t=int(t0),
        tr="",
        E=str(E0),
        hist=[],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", required=True, type=str, help="path to TM program JSON")
    ap.add_argument("--input", default="", type=str, help="input bitstring written at tape position 0")
    ap.add_argument("--max_steps", default=10_000, type=int)
    ap.add_argument("--reversible", action="store_true", help="enable Bennett history recording for TM steps")
    ap.add_argument("--commit", action="store_true", help="enable deterministic commit (beam truncation)")
    ap.add_argument("--coupled_every", default=0, type=int, help="if >0, apply one U_STEP every k TM steps")

    ap.add_argument("--m", default=6, type=int, help="macro window length m")
    ap.add_argument("--y", default="0" * 6, type=str, help="macro y bits low-to-high, length m")
    ap.add_argument("--t0", default="", type=str, help="initial tail-head bits low-to-high, length L(m); empty means all-zeros")
    ap.add_argument("--E0", default="1", type=str, help="initial energy tape bits; last bit is popped first")
    args = ap.parse_args()

    prog = TMProgram.from_json(Path(args.program))
    m = int(args.m)
    y_bits = str(args.y).strip()
    if len(y_bits) != m:
        raise SystemExit(f"--y must have length m={m} (low-to-high), got len={len(y_bits)}")

    br0 = _init_branch(
        program=prog,
        input_bits=str(args.input).strip(),
        m=m,
        y_bits_low_to_high=y_bits,
        t0_bits_low_to_high=str(args.t0).strip(),
        E0=str(args.E0).strip(),
    )

    last_print_s = [_now_s()]
    branches = run(
        program=prog,
        branch0=br0,
        max_steps=int(args.max_steps),
        reversible=bool(args.reversible),
        coupled_every=int(args.coupled_every),
        do_commit=bool(args.commit),
        last_print_s=last_print_s,
    )

    print(f"[observer_tm_ref] done branches={len(branches)}", flush=True)
    for i, b in enumerate(branches):
        out = b.tape.read_from_zero_until_blank()
        t_bits = _int_to_bitstring_low_to_high(b.t, width=b.L)
        print(
            f"[observer_tm_ref] branch={i} q={b.q} hp={b.hp} out={out!r} "
            f"t={t_bits} tr={b.tr!r} |E|={len(b.E)} |hist|={len(b.hist)}",
            flush=True,
        )


if __name__ == "__main__":
    main()

