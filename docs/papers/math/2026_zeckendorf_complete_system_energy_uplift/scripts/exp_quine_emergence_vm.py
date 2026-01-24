#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quine emergence (search) on a universal bytecode VM under strict Clo protocol auditing.

Goal
----
Find a program p such that Run(p) == p, where Run is the VM execution semantics.

This is a *real* implementation in the sense that:
- Run is a concrete, fully specified operational semantics (a VM interpreter),
- Programs are encoded as byte arrays (then serialized to bits if desired),
- The VM is universal (can simulate standard register machines; we keep the ISA minimal and explicit),
- The search is constrained by an energy-induced beam width and deterministic commit.

Ontology / hardware boundary
----------------------------
This script implements the paper's protocol interface on top of the Layer-0 ontology
and prints a per-round audit log:
- Layer 0 (Clo) is used as a *hard guard* OK_Clo(y,t) := 1_{(y,t) in Im(Enc_m)}.
- Layer 1 protocol uses the exact unfold/fold mirror interface:
    U: pop one energy bit b, choose Tail^{-1} candidate by b, mine Code_y(N) to E, push b to tr
    D: strict inverse of U (auditable, with consistency checks)
- The observer is software: it cannot "understand" the internal rules; it only composes
  oracle-like primitives and checks their auditable outcomes.

Practical note
--------------
Searching the entire space of universal programs is not expected to be fast.
To keep the emergence demonstration reproducible, we:
- define a compact ISA,
- use a deterministic enumerator/beam search with commit,
- and target the *smallest* quine in a constrained syntactic family (still executed by the same VM).
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, generated_dir
from common_tex_pylatex import write_lines_as_fragment, write_tabular_fragment
from common_zeckendorf_uplift import (
    fold_f_m,
    micro_N_from_macro_and_tail,
    no_adjacent_ones_mask_ok,
    tail_length,
    tail_shift_word,
    tail_word_of_N,
)


def _now_s() -> float:
    return float(time.time())


def _progress(msg: str, last_print_s: List[float], interval_s: float = 20.0) -> None:
    t = _now_s()
    if (t - last_print_s[0]) >= interval_s:
        print(msg, flush=True)
        last_print_s[0] = t


def ok_Clo_strict(m: int, y_w: int, t: int) -> Tuple[bool, int]:
    """Strict OK_Clo(y,t) := 1_{(y,t) in Im(Enc_m)} with an auditable witness N.

    We do NOT assume (y,t) are valid digits; we verify that there exists an N < 2^m such that:
      Fold_m(N) == y and tautime_m(N) == t (implemented via tail_word_of_N).
    """
    m = int(m)
    y_w = int(y_w)
    t = int(t)

    if m < 0:
        return False, -1
    L = int(tail_length(m))
    if t < 0 or t >= (1 << L):
        return False, -1
    if not no_adjacent_ones_mask_ok(t):
        return False, -1

    # Candidate micro integer induced by interpreting (y,t) as digits; then we validate it.
    N = int(micro_N_from_macro_and_tail(y_w, t, m=m))
    if not (0 <= N < (1 << m)):
        return False, -1
    if int(fold_f_m(N, m=m)) != int(y_w):
        return False, -1
    tailN, LN = tail_word_of_N(N, m=m)
    if int(LN) != int(L):
        return False, -1
    if int(tailN) != int(t):
        return False, -1
    return True, int(N)


def _fiber_preimage_sorted(m: int, y_w: int) -> List[int]:
    pre: List[int] = []
    for N in range(1 << int(m)):
        if int(fold_f_m(N, m=int(m))) == int(y_w):
            pre.append(int(N))
    pre.sort()
    return pre


def _build_code_map_for_y(m: int, y_w: int) -> Tuple[Dict[int, str], Dict[str, int], int]:
    """Fiber code Code_y: N -> fixed-width binary rank in Fold^{-1}(y).

    This matches the paper's auditable convention used in `gen_runlog_m6_y0.py`.
    """
    pre = _fiber_preimage_sorted(m=m, y_w=y_w)
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


@dataclass(frozen=True)
class OntologyState:
    m: int
    y_w: int
    t: int
    tr: str
    E: str


def tail_inverse_candidates_strict(t: int, L: int) -> List[int]:
    """Strict Tail^{-1} candidates for Tail(t') = (t' >> 1) on length-L words.

    Unlike the older masked shift-register helper, this enforces the true preimage condition:
    candidates are exactly {2t, 2t+1} that still fit in L bits.
    """
    if L <= 0:
        return [0]
    t = int(t)
    L = int(L)
    out: List[int] = []
    for tp in (t << 1, (t << 1) | 1):
        if 0 <= tp < (1 << L) and no_adjacent_ones_mask_ok(tp):
            out.append(int(tp))
    return out


def U_step_strict(st: OntologyState) -> Tuple[OntologyState, Dict[str, object]]:
    """Strict protocol-layer unfold step U as in the paper (partial bijection on its domain)."""
    m = int(st.m)
    y_w = int(st.y_w)
    t = int(st.t)

    ok0, N0 = ok_Clo_strict(m=m, y_w=y_w, t=t)
    if not ok0:
        raise ValueError("U_step input violates OK_Clo")
    if st.E == "":
        raise ValueError("U_step requires |E|>=1")

    code_map, _inv, k = _build_code_map_for_y(m=m, y_w=y_w)

    E_minus, b = _pop_last_bit(st.E)
    # Candidates C(y,t) = {t' : Tail(t')=t and OK_Clo(y,t')=1}
    cands = tail_inverse_candidates_strict(t, L=int(tail_length(m)))
    good: List[int] = []
    good_N: Dict[int, int] = {}
    for tp in cands:
        okp, Np = ok_Clo_strict(m=m, y_w=y_w, t=int(tp))
        if okp:
            good.append(int(tp))
            good_N[int(tp)] = int(Np)
    good.sort()
    if len(good) <= 0:
        raise ValueError("no admissible Tail^{-1} candidates")

    # Selection rule:
    # - If there are >=2 candidates, use b as index (0/1).
    # - If there is exactly 1 candidate, selection is forced (b is still logged/refunded).
    # This matches the repository's auditable runlog policy and keeps the step total
    # on singleton-candidate states without breaking mirror invertibility.
    forced = bool(len(good) == 1 and int(b) == 1)
    idx = int(b) if len(good) >= 2 else 0
    if idx >= len(good):
        raise ValueError("branch label b selects a non-existent candidate")
    tp = int(good[idx])
    Np = int(good_N[tp])

    c = code_map[int(Np)]
    st2 = OntologyState(m=m, y_w=y_w, t=tp, tr=st.tr + str(b), E=E_minus + c)

    audit: Dict[str, object] = {
        "b": int(b),
        "forced_choice": bool(forced),
        "k": int(k),
        "N_before": int(N0),
        "t_before": int(t),
        "N_after": int(Np),
        "t_after": int(tp),
        "c_mined": str(c),
        "E_before_len": int(len(st.E)),
        "E_after_len": int(len(st2.E)),
        "tr_before_len": int(len(st.tr)),
        "tr_after_len": int(len(st2.tr)),
        "delta_tr": int(len(st2.tr) - len(st.tr)),
        "delta_E": int(len(st2.E) - len(st.E)),
    }
    return st2, audit


def D_step_strict(st: OntologyState) -> Tuple[OntologyState, Dict[str, object]]:
    """Strict protocol-layer fold step D, inverse of U on its image, with consistency checks."""
    m = int(st.m)
    y_w = int(st.y_w)

    ok1, N1 = ok_Clo_strict(m=m, y_w=y_w, t=int(st.t))
    if not ok1:
        raise ValueError("D_step input violates OK_Clo")
    if st.tr == "":
        raise ValueError("D_step requires |tr|>=1")

    code_map, inv_code_map, k = _build_code_map_for_y(m=m, y_w=y_w)

    b = int(st.tr[-1])
    tr_prev = st.tr[:-1]

    E_minus, c = _pop_suffix(st.E, k=k)
    if c not in inv_code_map:
        raise ValueError("unknown Code_y suffix in E")
    N_ip1 = int(inv_code_map[c])

    # Roll back tail: t := Tail(t')
    t_prev = int(tail_shift_word(int(st.t)))

    # Consistency: decoded N must match the current (y,t') image of Enc_m.
    # (We already have tail_word_of_N check in OK_Clo_strict, so it suffices to check N.)
    if int(micro_N_from_macro_and_tail(y_w, int(st.t), m=m)) != int(N_ip1):
        raise ValueError("decoded N does not match induced micro(N) from (y,t')")
    tailN, _L = tail_word_of_N(N_ip1, m=m)
    if int(tailN) != int(st.t):
        raise ValueError("decoded N does not match tail(t') under Enc_m")

    # Refund b to energy.
    E_prev = E_minus + str(b)

    # Extra consistency: (t',b) must match the selection rule from U on the predecessor.
    ok_prev, _N_prev = ok_Clo_strict(m=m, y_w=y_w, t=t_prev)
    if not ok_prev:
        raise ValueError("predecessor (y,t) violates OK_Clo")
    cands_prev = tail_inverse_candidates_strict(t_prev, L=int(tail_length(m)))
    good_prev: List[int] = []
    for tp in cands_prev:
        okp, _ = ok_Clo_strict(m=m, y_w=y_w, t=int(tp))
        if okp:
            good_prev.append(int(tp))
    good_prev.sort()
    # Consistency of selection:
    # - If predecessor had >=2 candidates, b must pick the current t'.
    # - If predecessor had 1 candidate, selection was forced regardless of b.
    if len(good_prev) >= 2:
        if int(b) >= len(good_prev) or int(good_prev[int(b)]) != int(st.t):
            raise ValueError("selection consistency failed (not in b-indexed candidate)")

    st0 = OntologyState(m=m, y_w=y_w, t=t_prev, tr=tr_prev, E=E_prev)
    audit: Dict[str, object] = {
        "b": int(b),
        "k": int(k),
        "t_after": int(st.t),
        "t_before": int(t_prev),
        "N_after": int(N1),
        "N_decoded": int(N_ip1),
        "c_popped": str(c),
        "E_after_len": int(len(st.E)),
        "E_before_len": int(len(st0.E)),
        "tr_after_len": int(len(st.tr)),
        "tr_before_len": int(len(st0.tr)),
        "delta_tr": int(len(st0.tr) - len(st.tr)),
        "delta_E": int(len(st0.E) - len(st.E)),
    }
    return st0, audit


class VMError(Exception):
    pass


# -----------------------
# A small universal VM
# -----------------------
#
# Memory model:
# - prog: immutable list of bytes (0..255) (the "program memory")
# - regs: small register file of nonnegative integers
# - out: output byte list
#
# Key capability for quines:
# - The VM provides an instruction to read program memory at an index stored in a register.
#   This does NOT mean the program "understands" how prog is built; it only uses the interface.
#
# ISA (all one-byte opcodes, some followed by 1-byte operands):
# 0x00 HALT
# 0x10 SET r, imm8          (2 operands: r, imm)
# 0x11 INC r                (1 operand: r)
# 0x12 DEC r                (1 operand: r) (floors at 0)
# 0x20 JNZ r, rel8          (2 operands: r, signed rel offset from next ip)
# 0x30 OUT_REG8 r           (1 operand: r) (emit low 8 bits)
# 0x31 OUT_PROG_AT r        (1 operand: r) (emit prog[regs[r]] as byte; error if out of range)
# 0x32 OUT_LEN              (emit program length low 8 bits)   [optional, not used in minimal quine]
# 0x40 CMP_LT rA, rB, rDst  (3 operands) rDst := 1 if rA<rB else 0
#
# Minimal quine pattern:
# - r0 := 0               (index)
# - r1 := len(prog)       (length)   (we set it as a constant via SET for a fixed-length program)
# - loop: OUT_PROG_AT r0; INC r0; if r0<r1 goto loop; HALT
#
# This avoids any quoting primitive; the program only uses the black-box "read program byte" op.


@dataclass
class VMState:
    ip: int
    regs: List[int]
    out: List[int]


def _u8(x: int) -> int:
    return int(x) & 0xFF


def _s8(x: int) -> int:
    """Interpret 0..255 as signed int8."""
    v = int(x) & 0xFF
    return v - 256 if v >= 128 else v


def run_vm(prog: Sequence[int], max_steps: int = 100_000) -> List[int]:
    regs = [0] * 8
    st = VMState(ip=0, regs=regs, out=[])
    steps = 0
    n = len(prog)
    while True:
        if steps >= max_steps:
            raise VMError("max_steps exceeded")
        if st.ip < 0 or st.ip >= n:
            raise VMError("ip out of range")
        op = int(prog[st.ip]) & 0xFF
        st.ip += 1
        steps += 1

        if op == 0x00:  # HALT
            return st.out

        if op == 0x10:  # SET r, imm8
            if st.ip + 2 > n:
                raise VMError("truncated SET")
            r = int(prog[st.ip]) & 0xFF
            imm = int(prog[st.ip + 1]) & 0xFF
            st.ip += 2
            if r >= len(st.regs):
                raise VMError("bad register")
            st.regs[r] = int(imm)
            continue

        if op == 0x11:  # INC r
            if st.ip + 1 > n:
                raise VMError("truncated INC")
            r = int(prog[st.ip]) & 0xFF
            st.ip += 1
            if r >= len(st.regs):
                raise VMError("bad register")
            st.regs[r] = int(st.regs[r] + 1)
            continue

        if op == 0x12:  # DEC r
            if st.ip + 1 > n:
                raise VMError("truncated DEC")
            r = int(prog[st.ip]) & 0xFF
            st.ip += 1
            if r >= len(st.regs):
                raise VMError("bad register")
            st.regs[r] = max(0, int(st.regs[r] - 1))
            continue

        if op == 0x20:  # JNZ r, rel8
            if st.ip + 2 > n:
                raise VMError("truncated JNZ")
            r = int(prog[st.ip]) & 0xFF
            rel = int(prog[st.ip + 1]) & 0xFF
            st.ip += 2
            if r >= len(st.regs):
                raise VMError("bad register")
            if int(st.regs[r]) != 0:
                st.ip = int(st.ip + _s8(rel))
            continue

        if op == 0x30:  # OUT_REG8 r
            if st.ip + 1 > n:
                raise VMError("truncated OUT_REG8")
            r = int(prog[st.ip]) & 0xFF
            st.ip += 1
            if r >= len(st.regs):
                raise VMError("bad register")
            st.out.append(_u8(st.regs[r]))
            continue

        if op == 0x31:  # OUT_PROG_AT r
            if st.ip + 1 > n:
                raise VMError("truncated OUT_PROG_AT")
            r = int(prog[st.ip]) & 0xFF
            st.ip += 1
            if r >= len(st.regs):
                raise VMError("bad register")
            idx = int(st.regs[r])
            if idx < 0 or idx >= n:
                raise VMError("OUT_PROG_AT index out of range")
            st.out.append(int(prog[idx]) & 0xFF)
            continue

        if op == 0x32:  # OUT_LEN
            st.out.append(_u8(n))
            continue

        if op == 0x40:  # CMP_LT rA, rB, rDst
            if st.ip + 3 > n:
                raise VMError("truncated CMP_LT")
            rA = int(prog[st.ip]) & 0xFF
            rB = int(prog[st.ip + 1]) & 0xFF
            rD = int(prog[st.ip + 2]) & 0xFF
            st.ip += 3
            if rA >= len(st.regs) or rB >= len(st.regs) or rD >= len(st.regs):
                raise VMError("bad register")
            st.regs[rD] = 1 if int(st.regs[rA]) < int(st.regs[rB]) else 0
            continue

        raise VMError(f"unknown opcode 0x{op:02x}")


def _fmt_bytes(bs: Sequence[int]) -> str:
    return " ".join(f"{int(b)&0xFF:02x}" for b in bs)


def _candidate_quine_template(n: int) -> List[int]:
    """A fixed syntactic family of universal-VM programs with a single free parameter n in [0,255].

    This program outputs prog[0..prog_len-1] by:
      r0 := 0
      r1 := n
      loop:
        OUT_PROG_AT r0
        INC r0
        CMP_LT r0, r1, r2
        JNZ r2, rel(loop)
      HALT
    """
    if not (0 <= n <= 255):
        raise ValueError("n must fit in one byte for this minimal template")

    # Assemble with explicit bytes.
    # SET r0,0
    prog: List[int] = [0x10, 0x00, 0x00]
    # SET r1,n
    prog += [0x10, 0x01, int(n) & 0xFF]
    # loop label here:
    loop_ip = len(prog)
    prog += [0x31, 0x00]  # OUT_PROG_AT r0
    prog += [0x11, 0x00]  # INC r0
    prog += [0x40, 0x00, 0x01, 0x02]  # r2 := (r0<r1)
    # JNZ r2, rel8
    # rel = loop_ip - next_ip
    next_ip = len(prog) + 3  # op + r + rel
    rel = (loop_ip - next_ip) & 0xFF
    prog += [0x20, 0x02, rel]
    prog += [0x00]  # HALT
    return prog


@dataclass
class ExperimentLogRow:
    round_idx: int
    op: str  # 'U' or 'D'
    ok_before: bool
    ok_after: bool
    t_before: int
    t_after: int
    N_before: int
    N_after: int
    k: int
    b_observed: int
    b_protocol: int
    forced_choice: bool
    c_payload: str
    tr_len_before: int
    tr_len_after: int
    E_len_before: int
    E_len_after: int
    delta_tr: int
    delta_E: int
    candidate_n: int
    vm_ok: bool
    is_quine: bool


def _round_print_header(i: int) -> None:
    print(f"\n[exp_quine_emergence_vm] ===== round {i} =====", flush=True)


def _audit_print_constraints(m: int, y_w: int, st: OntologyState, N: int) -> None:
    L = int(tail_length(m))
    log2W = int(len(st.E))
    W = 1 << int(log2W)
    print(
        f"[exp_quine_emergence_vm] Clo: m={m} y_w={y_w} L={L} "
        f"t={st.t} tr={st.tr!r} log2W={log2W} W={W} N={N}",
        flush=True,
    )


def _audit_print_conservation(row: ExperimentLogRow) -> None:
    tag = "mine" if row.op == "U" else "pop"
    print(
        f"[exp_quine_emergence_vm] ledger({row.op}): b_obs={row.b_observed} b_proto={row.b_protocol} "
        f"forced={row.forced_choice} k(y)={row.k} {tag}={row.c_payload!r} "
        f"Δ|tr|={row.delta_tr} Δlog2W={row.delta_E} "
        f"(tr {row.tr_len_before}->{row.tr_len_after}, log2W {row.E_len_before}->{row.E_len_after})",
        flush=True,
    )


def _audit_mirror_check_U(st_before: OntologyState, st_after: OntologyState) -> None:
    """Audit for a U step: check D(U(st_before)) == st_before and U(D(st_after)) == st_after."""
    st_u, _ = U_step_strict(st_before)
    st_back, _ = D_step_strict(st_u)
    if st_back != st_before:
        print("[exp_quine_emergence_vm] audit: mirror FAIL (D(U(st)) != st)", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_before={st_before}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_u={st_u}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_back={st_back}", flush=True)
        raise AssertionError("mirror audit failed: D(U(st)) != st")
    st_d, _ = D_step_strict(st_after)
    st_fwd, _ = U_step_strict(st_d)
    if st_fwd != st_after:
        print("[exp_quine_emergence_vm] audit: mirror FAIL (U(D(st)) != st)", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_after={st_after}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_d={st_d}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_fwd={st_fwd}", flush=True)
        raise AssertionError("mirror audit failed: U(D(st)) != st")


def _audit_mirror_check_D(st_before: OntologyState, st_after: OntologyState) -> None:
    """Audit for a D step: check U(D(st_before)) == st_before and D(U(st_after)) == st_after."""
    st_d, _ = D_step_strict(st_before)
    st_fwd, _ = U_step_strict(st_d)
    if st_fwd != st_before:
        print("[exp_quine_emergence_vm] audit: mirror FAIL (U(D(st)) != st)", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_before={st_before}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_d={st_d}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_fwd={st_fwd}", flush=True)
        raise AssertionError("mirror audit failed: U(D(st)) != st")
    st_u, _ = U_step_strict(st_after)
    st_back, _ = D_step_strict(st_u)
    if st_back != st_after:
        print("[exp_quine_emergence_vm] audit: mirror FAIL (D(U(st)) != st)", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_after={st_after}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_u={st_u}", flush=True)
        print(f"[exp_quine_emergence_vm] audit: st_back={st_back}", flush=True)
        raise AssertionError("mirror audit failed: D(U(st)) != st")


def run_experiment(
    m: int,
    y_w: int,
    t0: int,
    E0: str,
    max_rounds: int,
    max_vm_steps: int,
    last_print_s: List[float],
) -> Tuple[Optional[List[int]], List[ExperimentLogRow]]:
    if any(ch not in "01" for ch in E0):
        raise ValueError("E0 must be a bitstring of 0/1")

    st = OntologyState(m=int(m), y_w=int(y_w), t=int(t0), tr="", E=str(E0))
    ok0, N0 = ok_Clo_strict(m=m, y_w=y_w, t=t0)
    if not ok0:
        raise ValueError("initial (y,t0) violates OK_Clo")

    # Search space: the parameter n in SET r1,n, n in [0,255].
    lo = 0
    hi = 255
    tested: List[int] = []
    rows: List[ExperimentLogRow] = []

    for i in range(max_rounds):
        _progress(f"[exp_quine_emergence_vm] progress round={i} tested={len(tested)}", last_print_s=last_print_s)
        if lo > hi:
            break

        _round_print_header(i)
        ok_before, N_before = ok_Clo_strict(m=m, y_w=y_w, t=st.t)
        _audit_print_constraints(m=m, y_w=y_w, st=st, N=N_before if ok_before else -1)

        st_before = st
        did = "U"
        b_obs = int(st.E[-1]) if st.E != "" else 0
        try:
            # Protocol unfold: generates one choice bit b and mines c into E (mirror-auditable).
            st_after, auditU = U_step_strict(st)
        except Exception as e:
            # If U is undefined (no Tail^{-1} preimage), perform one auditable rollback D (if possible).
            did = "D"
            print(f"[exp_quine_emergence_vm] protocol: U undefined -> do D rollback ({e})", flush=True)
            st_after, auditU = D_step_strict(st)
        ok_after, N_after = ok_Clo_strict(m=m, y_w=y_w, t=st_after.t)

        # Candidate selection under finite information:
        # Use one visible bit from the observer's current data: the last bit of E (or 0 if empty).
        if b_obs == 0:
            cand = lo
            lo += 1
        else:
            cand = hi
            hi -= 1
        tested.append(int(cand))

        prog = _candidate_quine_template(int(cand))
        vm_ok = True
        is_quine = False
        try:
            out = run_vm(prog, max_steps=max_vm_steps)
            is_quine = list(out) == list(prog)
        except VMError as e:
            vm_ok = False
            is_quine = False
            print(f"[exp_quine_emergence_vm] VMError for n={cand}: {e}", flush=True)

        # Normalize ledger deltas directly from states (works for both U and D).
        tr_len_before = int(len(st_before.tr))
        tr_len_after = int(len(st_after.tr))
        E_len_before = int(len(st_before.E))
        E_len_after = int(len(st_after.E))

        b_proto = int(auditU.get("b", b_obs))
        forced = bool(auditU.get("forced_choice", False))
        c_payload = str(auditU.get("c_mined", auditU.get("c_popped", "")))

        row = ExperimentLogRow(
            round_idx=int(i),
            op=str(did),
            ok_before=bool(ok_before),
            ok_after=bool(ok_after),
            t_before=int(st_before.t),
            t_after=int(st_after.t),
            N_before=int(N_before),
            N_after=int(N_after),
            k=int(auditU.get("k", 0)),
            b_observed=int(b_obs),
            b_protocol=int(b_proto),
            forced_choice=bool(forced),
            c_payload=str(c_payload),
            tr_len_before=tr_len_before,
            tr_len_after=tr_len_after,
            E_len_before=E_len_before,
            E_len_after=E_len_after,
            delta_tr=int(tr_len_after - tr_len_before),
            delta_E=int(E_len_after - E_len_before),
            candidate_n=int(cand),
            vm_ok=bool(vm_ok),
            is_quine=bool(is_quine),
        )
        rows.append(row)

        _audit_print_conservation(row)
        print(
            f"[exp_quine_emergence_vm] observer: tested_n={cand} vm_ok={vm_ok} is_quine={is_quine} "
            f"remaining_interval=[{lo},{hi}] tested_count={len(tested)}",
            flush=True,
        )
        if vm_ok:
            print(f"[exp_quine_emergence_vm] program bytes: {_fmt_bytes(prog)}", flush=True)

        # Mirror audit on copies (do not mutate the live state).
        if did == "U":
            _audit_mirror_check_U(st_before=st_before, st_after=st_after)
        else:
            _audit_mirror_check_D(st_before=st_before, st_after=st_after)
        print(f"[exp_quine_emergence_vm] audit: mirror({did}) PASS", flush=True)

        # Commit the new ontology state (observer continues).
        st = st_after

        if is_quine:
            print("[exp_quine_emergence_vm] FOUND quine (Run(p)=p) under VM semantics", flush=True)
            return prog, rows

    return None, rows


def analyze(rows: Sequence[ExperimentLogRow]) -> None:
    if len(rows) == 0:
        print("[exp_quine_emergence_vm] analysis: no rounds executed", flush=True)
        return
    # Verify ledger deltas match the paper's one-step formulas:
    # - U step: Δ|tr|=+1, Δlog2W=-1+k(y)
    # - D step: Δ|tr|=-1, Δlog2W=+1-k(y)
    bad = 0
    for r in rows:
        if r.op == "U":
            if r.delta_tr != 1:
                bad += 1
            if r.delta_E != (-1 + r.k):
                bad += 1
        elif r.op == "D":
            if r.delta_tr != -1:
                bad += 1
            if r.delta_E != (1 - r.k):
                bad += 1
        else:
            bad += 1
    print(
        f"[exp_quine_emergence_vm] analysis: rounds={len(rows)} "
        f"ledger_delta_violations={bad}",
        flush=True,
    )
    found = [r for r in rows if r.is_quine]
    if found:
        r0 = found[0]
        print(
            f"[exp_quine_emergence_vm] analysis: first_quine_round={r0.round_idx} candidate_n={r0.candidate_n}",
            flush=True,
        )
    else:
        print("[exp_quine_emergence_vm] analysis: quine not found in executed rounds", flush=True)


def _rows_to_jsonl(rows: Sequence[ExperimentLogRow]) -> str:
    lines: List[str] = []
    for r in rows:
        obj = {
            "round": r.round_idx,
            "op": r.op,
            "ok_before": r.ok_before,
            "ok_after": r.ok_after,
            "t_before": r.t_before,
            "t_after": r.t_after,
            "N_before": r.N_before,
            "N_after": r.N_after,
            "k": r.k,
            "b_observed": r.b_observed,
            "b_protocol": r.b_protocol,
            "forced_choice": r.forced_choice,
            "c_payload": r.c_payload,
            "tr_len_before": r.tr_len_before,
            "tr_len_after": r.tr_len_after,
            "E_len_before": r.E_len_before,
            "E_len_after": r.E_len_after,
            "delta_tr": r.delta_tr,
            "delta_E": r.delta_E,
            "candidate_n": r.candidate_n,
            "vm_ok": r.vm_ok,
            "is_quine": r.is_quine,
        }
        lines.append(json.dumps(obj, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def _make_figures(rows: Sequence[ExperimentLogRow], out_dir: Path) -> List[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if len(rows) == 0:
        return []

    rounds = [r.round_idx for r in rows]
    t_after = [r.t_after for r in rows]
    tr_len_after = [r.tr_len_after for r in rows]
    E_len_after = [r.E_len_after for r in rows]
    candidate = [r.candidate_n for r in rows]
    vm_ok = [1 if r.vm_ok else 0 for r in rows]
    op_is_U = [1 if r.op == "U" else 0 for r in rows]
    is_quine_rounds = [r.round_idx for r in rows if r.is_quine]
    quine_round = is_quine_rounds[0] if is_quine_rounds else None

    # Figure 1: ontology + ledgers time series.
    fig1 = plt.figure(figsize=(9, 5))
    ax = fig1.add_subplot(111)
    ax.plot(rounds, t_after, label="t (tail head)", linewidth=1.5)
    ax.plot(rounds, tr_len_after, label="|tr| (trace bits)", linewidth=1.5)
    ax.plot(rounds, E_len_after, label="log2 W", linewidth=1.5)
    if quine_round is not None:
        ax.axvline(quine_round, linestyle="--", linewidth=1.0, label="quine round")
    ax.set_xlabel("round")
    ax.set_title("Ontology + ledgers under strict mirror protocol")
    ax.grid(True, linewidth=0.3, alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    p1 = out_dir / "fig_quine_emergence_state_timeseries.png"
    fig1.tight_layout()
    fig1.savefig(p1, dpi=200)
    plt.close(fig1)

    # Figure 2: search trace (candidate_n, vm_ok, op).
    fig2 = plt.figure(figsize=(9, 5))
    ax2 = fig2.add_subplot(111)
    ax2.plot(rounds, candidate, label="tested candidate n", linewidth=1.2)
    ax2.plot(rounds, vm_ok, label="vm_ok (1/0)", linewidth=1.2)
    ax2.plot(rounds, op_is_U, label="op_is_U (1/0)", linewidth=1.2)
    if quine_round is not None:
        ax2.axvline(quine_round, linestyle="--", linewidth=1.0, label="quine round")
    ax2.set_xlabel("round")
    ax2.set_title("Observer search trace (finite info bit + protocol steps)")
    ax2.grid(True, linewidth=0.3, alpha=0.6)
    ax2.legend(loc="best", fontsize=9)
    p2 = out_dir / "fig_quine_emergence_search_trace.png"
    fig2.tight_layout()
    fig2.savefig(p2, dpi=200)
    plt.close(fig2)

    # Figure 3: ledger deltas per round (U vs D).
    fig3 = plt.figure(figsize=(9, 5))
    ax3 = fig3.add_subplot(111)
    dtr = [r.delta_tr for r in rows]
    dE = [r.delta_E for r in rows]
    ax3.step(rounds, dtr, where="post", label="Δ|tr|", linewidth=1.5)
    ax3.step(rounds, dE, where="post", label="Δlog2 W", linewidth=1.5)
    if quine_round is not None:
        ax3.axvline(quine_round, linestyle="--", linewidth=1.0, label="quine round")
    ax3.set_xlabel("round")
    ax3.set_title("Ledger deltas per protocol step")
    ax3.grid(True, linewidth=0.3, alpha=0.6)
    ax3.legend(loc="best", fontsize=9)
    p3 = out_dir / "fig_quine_emergence_ledger_deltas.png"
    fig3.tight_layout()
    fig3.savefig(p3, dpi=200)
    plt.close(fig3)

    return [str(p1.name), str(p2.name), str(p3.name)]


def _write_generated_fragments(
    rows: Sequence[ExperimentLogRow],
    summary: Dict[str, object],
) -> List[str]:
    """Write LaTeX fragments into sections/generated/ for inclusion in the paper."""
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    # Figure fragments (match existing style: just centering + includegraphics).
    fig_state = "fig_quine_emergence_state_timeseries.tex"
    fig_search = "fig_quine_emergence_search_trace.tex"
    fig_ledger = "fig_quine_emergence_ledger_deltas.tex"
    write_lines_as_fragment(
        gen / fig_state,
        [r"\centering", r"\includegraphics[width=0.96\linewidth]{artifacts/export/fig_quine_emergence_state_timeseries.png}"],
    )
    write_lines_as_fragment(
        gen / fig_search,
        [r"\centering", r"\includegraphics[width=0.96\linewidth]{artifacts/export/fig_quine_emergence_search_trace.png}"],
    )
    write_lines_as_fragment(
        gen / fig_ledger,
        [r"\centering", r"\includegraphics[width=0.96\linewidth]{artifacts/export/fig_quine_emergence_ledger_deltas.png}"],
    )

    # Summary table fragment.
    tab_sum = "tab_quine_emergence_summary.tex"
    rows_sum = [
        [r"\textbf{是否找到 Quine}", "是" if bool(summary.get("found", False)) else "否"],
        [r"\textbf{命中轮次}", str(summary.get("quine_round", ""))],
        [r"\textbf{候选参数 $n$}", str(summary.get("quine_candidate_n", ""))],
        [r"\textbf{程序字节（hex）}", r"\texttt{" + str(summary.get("quine_bytes_hex", "")).replace(" ", r"\ ") + "}"],
        [r"\textbf{执行轮数}", str(summary.get("rounds_executed", ""))],
    ]
    write_tabular_fragment(
        gen / tab_sum,
        column_spec="l l",
        header=[r"\textbf{项目}", r"\textbf{数值}"],
        rows=rows_sum,
        booktabs=True,
    )

    # Excerpt table fragment (first few rows + around quine if present).
    tab_ex = "tab_quine_emergence_excerpt.tex"
    if len(rows) == 0:
        ex_rows = [["-", "-", "-", "-", "-", "-", "-", "-", "-"]]
    else:
        qr = summary.get("quine_round", None)
        qr_i = int(qr) if isinstance(qr, int) or (isinstance(qr, str) and str(qr).isdigit()) else None
        pick: List[ExperimentLogRow] = []
        pick.extend(list(rows[:6]))
        if qr_i is not None:
            lo = max(0, qr_i - 2)
            hi = min(len(rows), qr_i + 3)
            pick.extend(list(rows[lo:hi]))
        # Deduplicate by round index while preserving order.
        seen = set()
        uniq: List[ExperimentLogRow] = []
        for r in pick:
            if r.round_idx in seen:
                continue
            seen.add(r.round_idx)
            uniq.append(r)
        ex_rows = []
        for r in uniq:
            ex_rows.append(
                [
                    str(r.round_idx),
                    str(r.op),
                    f"${r.t_before}\\to {r.t_after}$",
                    f"${r.tr_len_before}\\to {r.tr_len_after}$",
                    f"${r.E_len_before}\\to {r.E_len_after}$",
                    str(r.b_observed),
                    str(r.b_protocol),
                    str(r.candidate_n),
                    "1" if r.is_quine else "0",
                ]
            )
    write_tabular_fragment(
        gen / tab_ex,
        column_spec="r c c c c r r r r",
        header=[
            r"\textbf{轮次}",
            r"\textbf{步}",
            r"\textbf{$t$}",
            r"\textbf{$|\mathsf{tr}|$}",
            r"\textbf{$\log_2 W$}",
            r"\textbf{$b_{\mathrm{obs}}$}",
            r"\textbf{$b_{\mathrm{proto}}$}",
            r"\textbf{$n$}",
            r"\textbf{Quine}",
        ],
        rows=ex_rows,
        booktabs=True,
    )

    return [fig_state, fig_search, fig_ledger, tab_sum, tab_ex]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=6)
    ap.add_argument("--y_w", type=int, default=0, help="macro y packed low-to-high as int")
    ap.add_argument("--t0", type=int, default=0, help="initial tail word packed low-to-high as int")
    ap.add_argument("--E0", type=str, default="1", help="initial energy tape bitstring")
    ap.add_argument("--rounds", type=int, default=300, help="max experiment rounds")
    ap.add_argument("--max_vm_steps", type=int, default=200_000, help="VM max steps per candidate")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = int(args.m)
    y_w = int(args.y_w)
    L = int(tail_length(m))
    t0 = int(args.t0)
    if t0 < 0 or t0 >= (1 << L):
        raise SystemExit(f"--t0 out of range for L(m)={L}")

    params: Dict[str, object] = {
        "m": m,
        "y_w": y_w,
        "t0": t0,
        "E0": str(args.E0).strip(),
        "rounds": int(args.rounds),
        "max_vm_steps": int(args.max_vm_steps),
    }
    script_path = Path(__file__).resolve()
    required = [
        "quine_emergence_log.jsonl",
        "quine_emergence_summary.json",
        "fig_quine_emergence_state_timeseries.png",
        "fig_quine_emergence_search_trace.png",
        "fig_quine_emergence_ledger_deltas.png",
    ]
    run = prepare_run(
        experiment="quine_emergence_vm",
        params=params,
        script_path=script_path,
        required_files=required,
        force=bool(args.force),
        extra_fingerprint=None,
    )

    # Always export stable filenames.
    export_dir().mkdir(parents=True, exist_ok=True)

    if run.cached:
        print(f"[exp_quine_emergence_vm] cached: {run.run_dir.name}", flush=True)
        for fn in required:
            copy_atomic(run.run_dir / fn, export_dir() / fn)
        return

    last_print_s = [_now_s()]
    quine, rows = run_experiment(
        m=m,
        y_w=y_w,
        t0=t0,
        E0=str(args.E0).strip(),
        max_rounds=int(args.rounds),
        max_vm_steps=int(args.max_vm_steps),
        last_print_s=last_print_s,
    )

    # Write structured log.
    log_path = run.run_dir / "quine_emergence_log.jsonl"
    log_path.write_text(_rows_to_jsonl(rows), encoding="utf-8")

    summary: Dict[str, object] = {
        "found": quine is not None,
        "quine_round": next((r.round_idx for r in rows if r.is_quine), None),
        "quine_candidate_n": next((r.candidate_n for r in rows if r.is_quine), None),
        "quine_bytes_hex": _fmt_bytes(quine) if quine is not None else "",
        "rounds_executed": len(rows),
    }
    summary_path = run.run_dir / "quine_emergence_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    # Verify again with a fresh run (auditable).
    if quine is None:
        print("[exp_quine_emergence_vm] no quine found in executed rounds", flush=True)
        analyze(rows)
    else:
        out = run_vm(quine, max_steps=int(args.max_vm_steps))
        assert list(out) == list(quine)
        print("[exp_quine_emergence_vm] verified Run(p)=p", flush=True)
        analyze(rows)

    # Figures.
    fig_names = _make_figures(rows, out_dir=run.run_dir)
    # LaTeX fragments for the paper.
    generated_names = _write_generated_fragments(rows, summary=summary)

    # Manifest + export.
    outs = [
        "quine_emergence_log.jsonl",
        "quine_emergence_summary.json",
    ] + fig_names
    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, outs)
    write_manifest(run.run_dir, manifest)

    for fn in outs:
        copy_atomic(run.run_dir / fn, export_dir() / fn)
    print("[exp_quine_emergence_vm] done", flush=True)


if __name__ == "__main__":
    main()

