#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POM ISA reference simulator (executable).

This file implements exactly the ISA/microcode spec given in the prompt:

- 32 visible Z registers (Z0..Z31) with default P_Z writeback semantics modeled
  via an explicit Fold_∞ (Zeckendorf normalization) gate count k_Z.
- Micro-visible W registers (windows / raw bitstrings in Ω_m) to implement:
    Fold_m,  rem_{m+1→m} = π_{m+1→m} ∘ Fold_{m+1},
    r_{m+1→m} (direct truncation),
    gauge defect G_m = | r ⊕ rem |_0.
  The RESCALE↓ support budget is tracked as `support += G_m`.
- Optional P registers (prime-exponent vectors) for multiplicative linearization.

Cost counters align with the paper-style model:
  T_I(n) = k_Z * δ_Z + k_≤ * T_≤(n) + D_U(n)
and we additionally expose `support` for RESCALE↓ (gauge) operations.

Run:
  python3 pom_isa_sim.py --demo
  python3 pom_isa_sim.py --gauge --m 10 --trials 20000
"""

from __future__ import annotations

import argparse
import dataclasses
import random
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


U32_MASK = 0xFFFF_FFFF


# =========================
# Fibonacci / Zeckendorf
# =========================


def _fib_up_to_index(n: int) -> List[int]:
    """Return [F0, F1, ..., Fn] with F0=0,F1=1."""
    if n < 0:
        raise ValueError("n must be >= 0")
    fibs = [0, 1]
    while len(fibs) <= n:
        fibs.append(fibs[-1] + fibs[-2])
    return fibs


def _fib_weights(m: int) -> List[int]:
    """Return weights for positions k=1..m: (F_{k+1}) = (F2..F_{m+1})."""
    if m < 0:
        raise ValueError("m must be >= 0")
    fibs = _fib_up_to_index(m + 1)
    # indices 2..m+1 inclusive
    return fibs[2 : (m + 2)]


def zeckendorf_bits_nonneg(n: int) -> List[int]:
    """Greedy Zeckendorf representation bits for n>=0.

    Bits are returned low-to-high:
      bit[i] corresponds to Fibonacci weight F_{i+2} = F_{(i+1)+1}.
      i=0 -> F2=1, i=1 -> F3=2, ...
    """
    if n < 0:
        raise ValueError("n must be nonnegative")
    if n == 0:
        return []

    # Build Fibonacci weights [F2,F3,...,Fk] with last <= n
    fibs = [1, 2]  # F2, F3
    while fibs[-1] <= n:
        fibs.append(fibs[-1] + fibs[-2])
    if fibs[-1] > n:
        fibs.pop()

    bits = [0] * len(fibs)
    rem = n
    i = len(fibs) - 1
    while rem > 0 and i >= 0:
        if fibs[i] <= rem:
            bits[i] = 1
            rem -= fibs[i]
            i -= 2  # skip next lower to avoid consecutive ones
        else:
            i -= 1
    return bits


def _pack_bits(bits: Sequence[int], m: int) -> int:
    x = 0
    for i in range(min(m, len(bits))):
        if bits[i] & 1:
            x |= 1 << i
    return x


def _unpack_bits(x: int, m: int) -> List[int]:
    return [1 if ((x >> i) & 1) else 0 for i in range(m)]


def fold_infty_int(x: int) -> int:
    """Fold_∞ as the normalization projection P_Z.

    Truth layer is integer semantics; Fold_∞ is an idempotent normalization gate.
    We keep the integer value unchanged and count the gate via k_Z.
    """
    return int(x)


def window_N(omega_bits: int, m: int) -> int:
    """N(ω)=Σ_{k=1..m} ω_k F_{k+1} for raw window bits ω (low-to-high)."""
    if m < 0:
        raise ValueError("m must be >= 0")
    weights = _fib_weights(m)
    s = 0
    for i, w in enumerate(weights):
        if (omega_bits >> i) & 1:
            s += w
    return s


def fold_m_bits(omega_bits: int, m: int) -> int:
    """Fold_m(ω) = π_m(Z(N(ω))) as an m-bit Zeckendorf-legal string (packed int)."""
    if m < 0:
        raise ValueError("m must be >= 0")
    N = window_N(omega_bits, m)
    zb = zeckendorf_bits_nonneg(N)
    if len(zb) < m:
        zb = list(zb) + [0] * (m - len(zb))
    return _pack_bits(zb[:m], m=m)


def fold_m_int(omega_bits: int, m: int) -> int:
    """Integer value of Fold_m output embedded back into ℤ via Σ bit_k F_{k+1}."""
    fb = fold_m_bits(omega_bits, m)
    weights = _fib_weights(m)
    s = 0
    for i, w in enumerate(weights):
        if (fb >> i) & 1:
            s += w
    return s


def rem_mplus1_to_m_bits(omega_bits_mplus1: int, m: int) -> int:
    """rem_{m+1→m}(ω) = π_{m+1→m}(Fold_{m+1}(ω)) (packed m-bit int)."""
    if m < 0:
        raise ValueError("m must be >= 0")
    folded_mplus1 = fold_m_bits(omega_bits_mplus1, m + 1)
    return folded_mplus1 & ((1 << m) - 1) if m > 0 else 0


def trunc_mplus1_to_m_bits(omega_bits_mplus1: int, m: int) -> int:
    """r_{m+1→m}(ω): direct restriction (drop top bit), packed m-bit int."""
    return omega_bits_mplus1 & ((1 << m) - 1) if m > 0 else 0


def gauge_Gm(omega_bits_mplus1: int, m: int) -> int:
    """G_m(ω)=| r_{m+1→m}(ω) ⊕ rem_{m+1→m}(ω) |_0 (Hamming weight)."""
    r = trunc_mplus1_to_m_bits(omega_bits_mplus1, m)
    rem = rem_mplus1_to_m_bits(omega_bits_mplus1, m)
    return int((r ^ rem).bit_count())


# =========================
# Prime vectors (P regs)
# =========================


@dataclass
class PrimeVector:
    sign: int  # -1,0,+1
    exps: Dict[int, int]  # prime -> exponent (>=0)

    def copy(self) -> "PrimeVector":
        return PrimeVector(sign=int(self.sign), exps=dict(self.exps))


def _factorize_abs(n: int) -> Dict[int, int]:
    x = int(n)
    if x < 0:
        x = -x
    exps: Dict[int, int] = {}
    if x in (0, 1):
        return exps
    p = 2
    while p * p <= x:
        while x % p == 0:
            exps[p] = exps.get(p, 0) + 1
            x //= p
        p = 3 if p == 2 else p + 2
    if x > 1:
        exps[x] = exps.get(x, 0) + 1
    return exps


def primevec_from_int(z: int) -> PrimeVector:
    z = int(z)
    if z == 0:
        return PrimeVector(sign=0, exps={})
    sign = -1 if z < 0 else 1
    exps = _factorize_abs(z)
    return PrimeVector(sign=sign, exps=exps)


def int_from_primevec(pv: PrimeVector) -> int:
    if pv.sign == 0:
        return 0
    x = 1
    for p, e in sorted(pv.exps.items()):
        if e <= 0:
            continue
        x *= int(p) ** int(e)
    return int(pv.sign) * x


def primevec_mul(a: PrimeVector, b: PrimeVector) -> PrimeVector:
    if a.sign == 0 or b.sign == 0:
        return PrimeVector(sign=0, exps={})
    out = a.copy()
    out.sign = int(a.sign) * int(b.sign)
    for p, e in b.exps.items():
        out.exps[p] = int(out.exps.get(p, 0)) + int(e)
    return out


def primevec_div_checked(a: PrimeVector, b: PrimeVector) -> PrimeVector:
    """Return a/b in exponent space; raise on underflow (non-divisible)."""
    if b.sign == 0:
        raise ZeroDivisionError("PDIV by zero prime-vector (represents 0)")
    if a.sign == 0:
        return PrimeVector(sign=0, exps={})
    out = a.copy()
    # Divide sign: since sign ∈ {±1}, division equals multiplication.
    out.sign = int(a.sign) * int(b.sign)
    for p, e in b.exps.items():
        cur = int(out.exps.get(p, 0))
        ne = cur - int(e)
        if ne < 0:
            raise ValueError(f"PDIV underflow at prime {p}: {cur} - {int(e)} < 0")
        if ne == 0:
            out.exps.pop(p, None)
        else:
            out.exps[p] = ne
    return out


# =========================
# ISA: encoding / decoding
# =========================


class Opcode:
    # Core control
    NOP = 0
    HALT = 1
    # Z-visible
    ZLI = 2
    ZMOV = 3
    ZFOLD = 4
    ZADD = 5
    ZSUB = 6
    ZMUL = 7
    ZDIVQ = 8
    ZDIVR = 9
    # W micro-visible
    WSETM = 10
    WLI = 11
    WFOLD = 12
    WREM = 13
    WTRUNC = 14
    WGAUGE = 15
    # P optional
    Z2P = 16
    P2Z = 17
    PMUL = 18
    PDIV = 19


@dataclass(frozen=True)
class Decoded:
    opcode: int
    rd: int = 0
    rs1: int = 0
    rs2: int = 0
    imm: int = 0
    fmt: str = "R"  # "R","I","J"


def _u32(x: int) -> int:
    return int(x) & U32_MASK


def enc_R(op: int, rd: int, rs1: int, rs2: int, imm11: int = 0) -> int:
    return _u32(((op & 0x3F) << 26) | ((rd & 0x1F) << 21) | ((rs1 & 0x1F) << 16) | ((rs2 & 0x1F) << 11) | (imm11 & 0x7FF))


def enc_I(op: int, rd: int, rs1: int, imm16: int) -> int:
    return _u32(((op & 0x3F) << 26) | ((rd & 0x1F) << 21) | ((rs1 & 0x1F) << 16) | (imm16 & 0xFFFF))


def enc_J(op: int, imm26: int) -> int:
    return _u32(((op & 0x3F) << 26) | (imm26 & 0x3FFFFFF))


def _sign_extend(x: int, bits: int) -> int:
    m = 1 << (bits - 1)
    x &= (1 << bits) - 1
    return (x ^ m) - m


_OP_FMT: Dict[int, str] = {
    Opcode.NOP: "R",
    Opcode.HALT: "R",
    Opcode.ZLI: "I",
    Opcode.ZMOV: "R",
    Opcode.ZFOLD: "R",
    Opcode.ZADD: "R",
    Opcode.ZSUB: "R",
    Opcode.ZMUL: "R",
    Opcode.ZDIVQ: "R",
    Opcode.ZDIVR: "R",
    Opcode.WSETM: "I",
    Opcode.WLI: "I",
    Opcode.WFOLD: "I",
    Opcode.WREM: "I",
    Opcode.WTRUNC: "I",
    Opcode.WGAUGE: "I",
    Opcode.Z2P: "R",
    Opcode.P2Z: "R",
    Opcode.PMUL: "R",
    Opcode.PDIV: "R",
}


def decode(word: int) -> Decoded:
    w = _u32(word)
    op = (w >> 26) & 0x3F
    fmt = _OP_FMT.get(op, "R")
    if fmt == "J":
        imm = w & 0x3FFFFFF
        return Decoded(opcode=op, imm=imm, fmt="J")
    rd = (w >> 21) & 0x1F
    rs1 = (w >> 16) & 0x1F
    if fmt == "I":
        imm16 = w & 0xFFFF
        # I-format immediates are sign-extended by default; callers can interpret as unsigned if needed.
        imm = _sign_extend(imm16, 16)
        return Decoded(opcode=op, rd=rd, rs1=rs1, imm=imm, fmt="I")
    rs2 = (w >> 11) & 0x1F
    imm11 = w & 0x7FF
    # imm11 is unsigned in this reference (unused for current opcodes).
    return Decoded(opcode=op, rd=rd, rs1=rs1, rs2=rs2, imm=imm11, fmt="R")


# =========================
# Assembler (typed registers)
# =========================


_REG_RE = re.compile(r"^([ZWP])(\d+)$", re.IGNORECASE)


def _parse_reg(tok: str) -> Tuple[str, int]:
    m = _REG_RE.match(tok.strip())
    if not m:
        raise ValueError(f"Bad register {tok!r}. Use Z0..Z31, W0..W31, P0..P31.")
    kind = m.group(1).upper()
    idx = int(m.group(2))
    if not (0 <= idx <= 31):
        raise ValueError("Register index out of range (0..31)")
    return kind, idx


def _parse_imm(tok: str) -> int:
    s = tok.strip().lower()
    if s.startswith("0x"):
        return int(s, 16)
    if s.startswith("-0x"):
        return -int(s[1:], 16)
    return int(s, 10)


@dataclass(frozen=True)
class AsmInst:
    name: str
    args: Tuple[str, ...]


def parse_asm_lines(lines: Iterable[str]) -> List[AsmInst]:
    out: List[AsmInst] = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        # commas -> spaces
        line = line.replace(",", " ")
        parts = [p for p in line.split() if p]
        if not parts:
            continue
        name = parts[0].upper()
        args = tuple(parts[1:])
        out.append(AsmInst(name=name, args=args))
    return out


def assemble(insts: Sequence[AsmInst]) -> List[int]:
    mc: List[int] = []
    for ins in insts:
        op = ins.name
        a = ins.args

        def need(n: int) -> None:
            if len(a) != n:
                raise ValueError(f"{op}: expected {n} args, got {len(a)}: {a}")

        if op == "NOP":
            mc.append(enc_R(Opcode.NOP, 0, 0, 0, 0))
            continue
        if op in ("HALT", "HLT"):
            mc.append(enc_R(Opcode.HALT, 0, 0, 0, 0))
            continue

        # ---- Z core ----
        if op == "ZLI":
            need(2)
            k_rd, rd = _parse_reg(a[0])
            if k_rd != "Z":
                raise ValueError("ZLI: rd must be a Z register")
            imm = _parse_imm(a[1])
            mc.append(enc_I(Opcode.ZLI, rd, 0, imm))
            continue
        if op == "ZMOV":
            need(2)
            k_rd, rd = _parse_reg(a[0])
            k_ra, ra = _parse_reg(a[1])
            if k_rd != "Z" or k_ra != "Z":
                raise ValueError("ZMOV: operands must be Z registers")
            mc.append(enc_R(Opcode.ZMOV, rd, ra, 0, 0))
            continue
        if op == "ZFOLD":
            need(2)
            k_rd, rd = _parse_reg(a[0])
            k_ra, ra = _parse_reg(a[1])
            if k_rd != "Z" or k_ra != "Z":
                raise ValueError("ZFOLD: operands must be Z registers")
            mc.append(enc_R(Opcode.ZFOLD, rd, ra, 0, 0))
            continue
        if op in ("ZADD", "ZSUB", "ZMUL", "ZDIVQ", "ZDIVR"):
            need(3)
            k_rd, rd = _parse_reg(a[0])
            k_ra, ra = _parse_reg(a[1])
            k_rb, rb = _parse_reg(a[2])
            if k_rd != "Z" or k_ra != "Z" or k_rb != "Z":
                raise ValueError(f"{op}: operands must be Z registers")
            opc = {
                "ZADD": Opcode.ZADD,
                "ZSUB": Opcode.ZSUB,
                "ZMUL": Opcode.ZMUL,
                "ZDIVQ": Opcode.ZDIVQ,
                "ZDIVR": Opcode.ZDIVR,
            }[op]
            mc.append(enc_R(opc, rd, ra, rb, 0))
            continue

        # ---- W micro ----
        if op == "WSETM":
            need(2)
            k_wd, wd = _parse_reg(a[0])
            if k_wd != "W":
                raise ValueError("WSETM: Wd must be a W register")
            mval = _parse_imm(a[1])
            mc.append(enc_I(Opcode.WSETM, wd, 0, mval))
            continue
        if op == "WLI":
            need(2)
            k_wd, wd = _parse_reg(a[0])
            if k_wd != "W":
                raise ValueError("WLI: Wd must be a W register")
            imm = _parse_imm(a[1])
            mc.append(enc_I(Opcode.WLI, wd, 0, imm))
            continue
        if op in ("WFOLD", "WREM", "WTRUNC", "WGAUGE"):
            need(3)
            k_d, d = _parse_reg(a[0])
            k_s, s = _parse_reg(a[1])
            mval = _parse_imm(a[2])
            opc = {"WFOLD": Opcode.WFOLD, "WREM": Opcode.WREM, "WTRUNC": Opcode.WTRUNC, "WGAUGE": Opcode.WGAUGE}[op]
            if op == "WFOLD":
                if k_d != "Z" or k_s != "W":
                    raise ValueError("WFOLD: signature is WFOLD Zd, Ws, m")
            elif op in ("WREM", "WTRUNC"):
                if k_d != "W" or k_s != "W":
                    raise ValueError(f"{op}: signature is {op} Wd, Ws, m")
            elif op == "WGAUGE":
                if k_d != "Z" or k_s != "W":
                    raise ValueError("WGAUGE: signature is WGAUGE Zd, Ws, m")
            mc.append(enc_I(opc, d, s, mval))
            continue

        # ---- P optional ----
        if op == "Z2P":
            need(2)
            k_pd, pd = _parse_reg(a[0])
            k_za, za = _parse_reg(a[1])
            if k_pd != "P" or k_za != "Z":
                raise ValueError("Z2P: signature is Z2P Pd, Za")
            mc.append(enc_R(Opcode.Z2P, pd, za, 0, 0))
            continue
        if op == "P2Z":
            need(2)
            k_zd, zd = _parse_reg(a[0])
            k_pa, pa = _parse_reg(a[1])
            if k_zd != "Z" or k_pa != "P":
                raise ValueError("P2Z: signature is P2Z Zd, Pa")
            mc.append(enc_R(Opcode.P2Z, zd, pa, 0, 0))
            continue
        if op in ("PMUL", "PDIV"):
            need(3)
            k_pd, pd = _parse_reg(a[0])
            k_pa, pa = _parse_reg(a[1])
            k_pb, pb = _parse_reg(a[2])
            if k_pd != "P" or k_pa != "P" or k_pb != "P":
                raise ValueError(f"{op}: operands must be P registers")
            mc.append(enc_R(Opcode.PMUL if op == "PMUL" else Opcode.PDIV, pd, pa, pb, 0))
            continue

        raise ValueError(f"Unknown instruction {op!r}")
    return mc


# =========================
# CPU state / execution
# =========================


@dataclass
class Window:
    bits: int = 0
    m: int = 0

    def masked_bits(self) -> int:
        if self.m <= 0:
            return 0
        return int(self.bits) & ((1 << int(self.m)) - 1)


@dataclass
class Counters:
    k_Z: int = 0
    k_le: int = 0
    D_U: int = 0
    support: int = 0
    n_max_bits: int = 0  # proxy for "n" in T_≤(n)


@dataclass
class CPU:
    Z: List[int]
    W: List[Window]
    P: List[PrimeVector]
    pc: int = 0
    halted: bool = False
    ctr: Counters = dataclasses.field(default_factory=Counters)

    @staticmethod
    def fresh() -> "CPU":
        return CPU(
            Z=[0 for _ in range(32)],
            W=[Window() for _ in range(32)],
            P=[PrimeVector(sign=0, exps={}) for _ in range(32)],
        )

    def _touch_n(self, *vals: int) -> None:
        for v in vals:
            b = int(abs(int(v))).bit_length()
            if b > self.ctr.n_max_bits:
                self.ctr.n_max_bits = b

    def _write_Z(self, rd: int, value: int, *, do_fold: bool) -> None:
        v = int(value)
        self._touch_n(v)
        if do_fold:
            self.ctr.k_Z += 1
            v = fold_infty_int(v)
        self.Z[int(rd)] = int(v)

    def _write_W(self, wd: int, bits: int, m: int) -> None:
        self.W[int(wd)].m = int(m)
        if m <= 0:
            self.W[int(wd)].bits = 0
        else:
            self.W[int(wd)].bits = int(bits) & ((1 << int(m)) - 1)

    def step(self, word: int) -> None:
        if self.halted:
            return
        ins = decode(word)
        op = ins.opcode

        def z(i: int) -> int:
            return int(self.Z[int(i)])

        def w_bits(i: int, m: int) -> int:
            if m <= 0:
                return 0
            return int(self.W[int(i)].bits) & ((1 << int(m)) - 1)

        if op == Opcode.NOP:
            self.pc += 1
            return
        if op == Opcode.HALT:
            self.halted = True
            return

        # ---- Z ----
        if op == Opcode.ZLI:
            imm = int(ins.imm)  # sign-extended
            self._write_Z(ins.rd, imm, do_fold=True)
            self.pc += 1
            return
        if op == Opcode.ZMOV:
            self._write_Z(ins.rd, z(ins.rs1), do_fold=False)
            self.pc += 1
            return
        if op == Opcode.ZFOLD:
            self._write_Z(ins.rd, z(ins.rs1), do_fold=True)
            self.pc += 1
            return
        if op in (Opcode.ZADD, Opcode.ZSUB, Opcode.ZMUL, Opcode.ZDIVQ, Opcode.ZDIVR):
            a = z(ins.rs1)
            b = z(ins.rs2)
            self._touch_n(a, b)
            if op == Opcode.ZADD:
                self._write_Z(ins.rd, a + b, do_fold=True)
            elif op == Opcode.ZSUB:
                self._write_Z(ins.rd, a - b, do_fold=True)
            elif op == Opcode.ZMUL:
                # D_U proxy: bitlength cost (linear-ish in operand size)
                self.ctr.D_U += abs(a).bit_length() + abs(b).bit_length()
                self._write_Z(ins.rd, a * b, do_fold=True)
            elif op == Opcode.ZDIVQ:
                self.ctr.k_le += 1
                if b == 0:
                    raise ZeroDivisionError("ZDIVQ by zero")
                self._write_Z(ins.rd, a // b, do_fold=True)
            elif op == Opcode.ZDIVR:
                self.ctr.k_le += 1
                if b == 0:
                    raise ZeroDivisionError("ZDIVR by zero")
                self._write_Z(ins.rd, a % b, do_fold=True)
            self.pc += 1
            return

        # ---- W ----
        if op == Opcode.WSETM:
            m = int(ins.imm)
            if m < 0:
                raise ValueError("WSETM m must be >= 0")
            cur = self.W[int(ins.rd)]
            cur.m = m
            cur.bits = cur.masked_bits()
            self.pc += 1
            return
        if op == Opcode.WLI:
            # Load low 16 bits (demo); interpret immediate as unsigned 16-bit payload.
            imm_u16 = int(ins.imm) & 0xFFFF
            cur = self.W[int(ins.rd)]
            m = int(cur.m)
            if m < 0:
                m = 0
            self._write_W(ins.rd, imm_u16, m=m)
            self.pc += 1
            return
        if op == Opcode.WFOLD:
            m = int(ins.imm)
            if m < 0:
                raise ValueError("WFOLD m must be >= 0")
            omega = w_bits(ins.rs1, m)
            val = fold_m_int(omega, m)
            # Table says k_Z += 1 for WFOLD (writeback normalization).
            self._write_Z(ins.rd, val, do_fold=True)
            self.pc += 1
            return
        if op in (Opcode.WREM, Opcode.WTRUNC, Opcode.WGAUGE):
            m = int(ins.imm)
            if m < 0:
                raise ValueError("W* m must be >= 0")
            omega_mplus1 = w_bits(ins.rs1, m + 1)
            if op == Opcode.WTRUNC:
                r = trunc_mplus1_to_m_bits(omega_mplus1, m)
                self._write_W(ins.rd, r, m=m)
            elif op == Opcode.WREM:
                g = gauge_Gm(omega_mplus1, m)
                self.ctr.support += int(g)
                rem = rem_mplus1_to_m_bits(omega_mplus1, m)
                self._write_W(ins.rd, rem, m=m)
            elif op == Opcode.WGAUGE:
                g = gauge_Gm(omega_mplus1, m)
                self.ctr.support += int(g)
                # WGAUGE writes an integer gauge value; spec table does not count k_Z here.
                self._write_Z(ins.rd, int(g), do_fold=False)
            self.pc += 1
            return

        # ---- P ----
        if op == Opcode.Z2P:
            pv = primevec_from_int(z(ins.rs1))
            self.P[int(ins.rd)] = pv
            self.pc += 1
            return
        if op == Opcode.P2Z:
            pv = self.P[int(ins.rs1)]
            val = int_from_primevec(pv)
            self._write_Z(ins.rd, val, do_fold=True)
            self.pc += 1
            return
        if op == Opcode.PMUL:
            a = self.P[int(ins.rs1)]
            b = self.P[int(ins.rs2)]
            self.P[int(ins.rd)] = primevec_mul(a, b)
            self.pc += 1
            return
        if op == Opcode.PDIV:
            # One feasibility/order check per spec.
            self.ctr.k_le += 1
            a = self.P[int(ins.rs1)]
            b = self.P[int(ins.rs2)]
            self.P[int(ins.rd)] = primevec_div_checked(a, b)
            self.pc += 1
            return

        raise ValueError(f"Unknown opcode {op} at pc={self.pc}")


def run_program(cpu: CPU, prog: Sequence[int], *, step_cap: int = 1_000_000) -> CPU:
    steps = 0
    while not cpu.halted:
        if not (0 <= cpu.pc < len(prog)):
            raise IndexError(f"PC out of range: pc={cpu.pc} len={len(prog)}")
        cpu.step(prog[cpu.pc])
        steps += 1
        if steps > step_cap:
            raise RuntimeError("step cap exceeded")
    return cpu


# =========================
# CLI demos
# =========================


def _demo_program_asm() -> List[str]:
    return [
        "ZLI Z1, 123",
        "ZLI Z2, 77",
        "ZADD Z3, Z1, Z2",
        "ZMUL Z4, Z1, Z2",
        "ZDIVQ Z5, Z1, Z2",
        "ZDIVR Z6, Z1, Z2",
        "HALT",
    ]


def cmd_demo() -> None:
    insts = parse_asm_lines(_demo_program_asm())
    prog = assemble(insts)
    cpu = CPU.fresh()
    run_program(cpu, prog)

    print("[demo] Z1=123  Z2=77", flush=True)
    print(f"[demo] Z3=Z1+Z2 => {cpu.Z[3]} (expect 200)", flush=True)
    print(f"[demo] Z4=Z1*Z2 => {cpu.Z[4]} (expect 9471)", flush=True)
    print(f"[demo] Z5=Z1//Z2 => {cpu.Z[5]} (expect 1)", flush=True)
    print(f"[demo] Z6=Z1%Z2  => {cpu.Z[6]} (expect 46)", flush=True)
    print(
        f"[demo] counters: k_Z={cpu.ctr.k_Z} k_le={cpu.ctr.k_le} D_U={cpu.ctr.D_U} support={cpu.ctr.support} n_bits~{cpu.ctr.n_max_bits}",
        flush=True,
    )


def cmd_gauge(m: int, trials: int, seed: Optional[int]) -> None:
    if m < 0:
        raise ValueError("--m must be >= 0")
    if trials <= 0:
        raise ValueError("--trials must be positive")
    rng = random.Random(seed)
    tot = 0
    mx = 0
    # sample ω uniformly in {0,1}^{m+1}
    for _ in range(trials):
        omega = rng.getrandbits(m + 1) if (m + 1) > 0 else 0
        g = gauge_Gm(omega, m)
        tot += g
        if g > mx:
            mx = g
    avg = tot / float(trials)
    ratio = (avg / float(m)) if m > 0 else 0.0
    print(f"[gauge] m={m} trials={trials} E[G_m]~{avg:.6g}  E[G_m]/m~{ratio:.6g}  max_seen={mx}  G_max=m={m}", flush=True)


def _T_le_default(n_bits: int) -> float:
    # Placeholder: order/feasibility projection cost grows mildly with input size.
    return float(max(1, n_bits))


def main() -> None:
    ap = argparse.ArgumentParser(description="POM ISA reference simulator (32-bit encoding + executable).")
    ap.add_argument("--demo", action="store_true", help="Run the built-in arithmetic demo.")
    ap.add_argument("--gauge", action="store_true", help="Run Monte Carlo gauge test for G_m.")
    ap.add_argument("--m", type=int, default=10, help="m for --gauge (uses ω in {0,1}^{m+1}).")
    ap.add_argument("--trials", type=int, default=20000, help="Trials for --gauge.")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for --gauge (deterministic).")
    ap.add_argument("--asm", type=str, default=None, help="Run an assembly file (no labels; # comments).")
    ap.add_argument("--deltaZ", type=float, default=1.0, help="δ_Z in T_I(n)=kZ*δZ+k≤*T≤(n)+DU.")
    ap.add_argument("--print-cost", action="store_true", help="After execution, print T_I(n) with a default T≤(n) proxy.")
    args = ap.parse_args()

    if args.demo:
        cmd_demo()
        return

    if args.gauge:
        cmd_gauge(m=int(args.m), trials=int(args.trials), seed=int(args.seed))
        return

    if args.asm is not None:
        path = str(args.asm)
        lines = open(path, "r", encoding="utf-8").read().splitlines()
        insts = parse_asm_lines(lines)
        prog = assemble(insts)
        cpu = CPU.fresh()
        run_program(cpu, prog)
        print(
            f"[run] halted pc={cpu.pc} counters: k_Z={cpu.ctr.k_Z} k_le={cpu.ctr.k_le} D_U={cpu.ctr.D_U} support={cpu.ctr.support} n_bits~{cpu.ctr.n_max_bits}",
            flush=True,
        )
        if args.print_cost:
            T = float(cpu.ctr.k_Z) * float(args.deltaZ) + float(cpu.ctr.k_le) * _T_le_default(cpu.ctr.n_max_bits) + float(cpu.ctr.D_U)
            print(f"[run] cost proxy: T_I~{T:.6g}  (δ_Z={float(args.deltaZ):g}, T_≤(n_bits)={_T_le_default(cpu.ctr.n_max_bits):g})", flush=True)
        return

    ap.print_help(sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()

