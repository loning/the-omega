#!/usr/bin/env python3
"""
Black-hole-equivalent system (computer science model) in discrete tick time.

This script implements a deterministic "black hole" as a black-box internal queue
plus a radiation output channel, using the same finite objects as the paper:
  - microstates: N in {0,..,2^m-1}
  - stable types: w in X_m (no consecutive ones)
  - truncation folding map: Fold_m: {0,..,2^m-1} -> X_m
  - fiber degeneracy: g_m(w)=|Fold_m^{-1}(w)|

Key ideas (CS-to-physics dictionary):
- tick: discrete time step
- mass/energy M: remaining service budget; decreases by 1 per radiation tick
- horizon/causal inaccessibility: the internal queue and internal state are not observable;
  the outside sees only radiation records (and optionally the remaining mass M)
- absorption: enqueue input microstates; increases mass by 1 per absorbed item
- radiation: dequeue one microstate (or vacuum if empty) and emit a stable type record;
  decreases mass by 1
- "unitarity" (CS model): the radiation record can be made information-complete without
  exposing a separate side channel. In this script we demonstrate a single-stream model
  in which the radiation is \\emph{only} a time-ordered stream of stable labels w in X_m:
    - early radiation emits only coarse labels w_i=Fold_m(N_i), which hides fiber information
    - late radiation emits additional stable labels that encode the fiber coordinates
  so that the full microstate stream is recoverable from radiation alone after evaporation.

Run:
  python3 scripts/exp_black_hole_queue_equivalence.py
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

from protocol_kernel import all_xm, cached_foldm_outputs, fold_m, split_cyc_bdry


MASK64 = (1 << 64) - 1

@dataclass
class BHState:
    """
    Internal (black-box) state.
    """

    mass: int
    m: int
    q: List[int]  # queue of microstates N in {0,..,2^m-1}
    stash_j: List[int]  # hidden fiber coordinates to be released later (kept internal)


def fiber_preimages(m: int) -> Dict[str, List[int]]:
    """
    Return preimages[w] = sorted list of microstate indices k with Fold_m(k)=w.
    """
    outs = cached_foldm_outputs(m)
    pre: Dict[str, List[int]] = {}
    for k, w in enumerate(outs):
        pre.setdefault(w, []).append(k)
    for w in pre:
        pre[w].sort()
    return pre


def _digits_per_fiber(m: int, preimages: Dict[str, List[int]], Xm: List[str]) -> int:
    """
    Number of base-|X_m| digits required to encode any fiber coordinate j in [0, g_m(w)).
    """
    A = len(Xm)
    if A <= 1:
        raise ValueError("Expected |X_m|>=2 for nontrivial encoding.")
    g_max = max(len(v) for v in preimages.values()) if preimages else 1
    if g_max <= 1:
        return 0
    # smallest t with A^t >= g_max
    t = 0
    cap = 1
    while cap < g_max:
        cap *= A
        t += 1
    return t


def _encode_base_A(x: int, A: int, t: int) -> List[int]:
    """
    Encode integer x in base A using exactly t digits (most-significant first).
    Requires 0 <= x < A^t.
    """
    if t <= 0:
        return []
    if x < 0:
        raise ValueError("x must be nonnegative")
    digits = [0] * t
    y = int(x)
    for i in range(t - 1, -1, -1):
        digits[i] = y % A
        y //= A
    if y != 0:
        raise ValueError("x does not fit in t base-A digits")
    return digits


def _decode_base_A(digits: List[int], A: int) -> int:
    y = 0
    for d in digits:
        if d < 0 or d >= A:
            raise ValueError("digit out of range")
        y = y * A + d
    return int(y)


def _interleave_schedule(
    L: int, t: int, scramble_delay: int, exponent: int
) -> List[str]:
    """
    Deterministic schedule for the non-vacuum portion of the radiation stream.

    We must place:
      - L payload emissions (coarse labels for the message microstates)
      - L*t recovery emissions (stable labels that encode fiber digits)
    into a single stream of length L + L*t.

    Rules:
      - For the first `scramble_delay` ticks (bounded by available payload), emit payload only.
      - After that, emit either payload or recovery by comparing weights:
          payload_weight  = (payload_remaining)^exponent
          recovery_weight = (recovery_remaining)
        Emit payload if payload_weight >= recovery_weight, else recovery.

    The resulting schedule exhibits a Page-like structure:
      early: payload dominates (coarse, low recoverability)
      late: recovery dominates (information release)

    Returns a list of tokens of length L + L*t, each in {"P","R"}.
    """
    if L < 0 or t < 0:
        raise ValueError("L and t must be nonnegative")
    if exponent < 1:
        raise ValueError("exponent must be >= 1")
    p_rem = int(L)
    r_rem = int(L) * int(t)
    total = p_rem + r_rem
    sched: List[str] = []
    warm = min(int(scramble_delay), p_rem)

    for i in range(total):
        if p_rem <= 0:
            sched.append("R")
            r_rem -= 1
            continue
        if r_rem <= 0:
            sched.append("P")
            p_rem -= 1
            continue
        if i < warm:
            sched.append("P")
            p_rem -= 1
            continue

        pw = float(p_rem) ** float(exponent)
        rw = float(r_rem)
        if pw >= rw:
            sched.append("P")
            p_rem -= 1
        else:
            sched.append("R")
            r_rem -= 1

    if p_rem != 0 or r_rem != 0:
        raise RuntimeError("Schedule construction failed to place all emissions")
    return sched


def _split_by_schedule(stream: List[str], schedule: List[str]) -> Tuple[List[str], List[str]]:
    """
    Given a mixed non-vacuum stream and the schedule, split into (payload_stream, recovery_stream).
    """
    if len(stream) != len(schedule):
        raise ValueError("stream and schedule must have the same length")
    payload: List[str] = []
    recovery: List[str] = []
    for w, tag in zip(stream, schedule):
        if tag == "P":
            payload.append(w)
        elif tag == "R":
            recovery.append(w)
        else:
            raise ValueError("invalid schedule tag")
    return payload, recovery


def _remaining_ambiguity_bits(
    g_list: List[int], A: int, t: int, payload_emitted: int, recovery_emitted: int
) -> float:
    """
    Surrogate remaining micro-ambiguity U in bits given:
      - payload_emitted: number of coarse labels emitted so far
      - recovery_emitted: number of recovery digits emitted so far

    Bound model:
      For a symbol with fiber size g and k revealed base-A digits (0<=k<=t),
      remaining ambiguity is bounded by log2 ceil(g / A^k).
    """
    if payload_emitted < 0 or recovery_emitted < 0:
        raise ValueError("emitted counts must be nonnegative")
    if t < 0:
        raise ValueError("t must be nonnegative")
    if A <= 1:
        raise ValueError("A must be >= 2")

    L = len(g_list)
    p = min(L, int(payload_emitted))
    r = min(L * t, int(recovery_emitted))
    if t == 0:
        return 0.0

    U = 0.0
    for i in range(p):
        g = int(g_list[i])
        # digits revealed for symbol i
        k = min(t, max(0, r - i * t))
        denom = 1
        for _ in range(int(k)):
            denom *= A
        rem = (g + denom - 1) // denom
        if rem > 1:
            U += math.log2(float(rem))
    return float(U)


def _cap_select_mixing_params(L: int, t: int, g_list: List[int], A: int) -> Dict[str, int]:
    """
    Deterministic finite-family selection for (scramble_delay, exponent).

    Objective:
      - Pick a schedule whose ambiguity surrogate peaks near the midpoint of the non-vacuum stream.
      - Tie-break prefers larger scramble_delay (more coarse early) and smaller exponent.
    """
    if L <= 0:
        return {"scramble_delay": 0, "exponent": 1}
    if t < 0:
        raise ValueError("t must be >= 0")

    total_nonvac = L + (L * t)
    target_peak = 0.5 * float(total_nonvac)

    delay_ratios = [0.0, 0.25, 1.0 / 3.0, 0.5, 2.0 / 3.0, 0.75]
    exponents = [1, 2, 3]

    best_key = None
    best = None

    for r0 in delay_ratios:
        scramble_delay = int(math.floor(float(r0) * float(L)))
        for exponent in exponents:
            sched = _interleave_schedule(L=L, t=t, scramble_delay=scramble_delay, exponent=exponent)
            payload_emitted = 0
            recovery_emitted = 0
            peak_idx = 0
            peak_val = -1.0
            for i, tag in enumerate(sched):
                if tag == "P":
                    payload_emitted += 1
                else:
                    recovery_emitted += 1
                U = _remaining_ambiguity_bits(
                    g_list=g_list,
                    A=A,
                    t=t,
                    payload_emitted=payload_emitted,
                    recovery_emitted=recovery_emitted,
                )
                if U > peak_val + 1e-12:
                    peak_val = U
                    peak_idx = i

            peak_tick = float(peak_idx + 1)
            peak_mismatch = abs(peak_tick - target_peak)
            key = (peak_mismatch, -scramble_delay, int(exponent))
            if best_key is None or key < best_key:
                best_key = key
                best = {"scramble_delay": int(scramble_delay), "exponent": int(exponent)}

    assert best is not None
    return best


def _escape_stream(stream: List[str], delim: str, esc: str) -> List[str]:
    """
    Deterministic escaping on the stable-label stream.

    Rule:
      - esc  -> esc esc
      - delim -> esc delim
      - other -> itself

    Property:
      - The escaped stream contains no consecutive (delim, delim) pair.
    """
    if esc == delim:
        raise ValueError("esc and delim must be distinct")
    out: List[str] = []
    for w in stream:
        if w == esc:
            out.extend([esc, esc])
        elif w == delim:
            out.extend([esc, delim])
        else:
            out.append(w)
    # Frame terminator: ensure escaped payload never ends with delim and never ends with a dangling escape.
    out.append(esc)
    return out


def _unescape_stream(stream: List[str], delim: str, esc: str) -> List[str]:
    """
    Inverse of _escape_stream.
    """
    if esc == delim:
        raise ValueError("esc and delim must be distinct")
    if not stream or stream[-1] != esc:
        raise RuntimeError("Missing escape terminator at end of escaped payload")
    body = stream[:-1]

    out: List[str] = []
    i = 0
    n = len(body)
    while i < n:
        w = body[i]
        if w != esc:
            if w == delim:
                raise RuntimeError("Found raw delimiter inside escaped payload")
            out.append(w)
            i += 1
            continue
        if i + 1 >= n:
            raise RuntimeError("Dangling escape token at end of escaped payload")
        w2 = body[i + 1]
        if w2 == esc:
            out.append(esc)
        elif w2 == delim:
            out.append(delim)
        else:
            raise RuntimeError("Invalid escape pair")
        i += 2
    return out


def _select_delim_esc(pre: Dict[str, List[int]], Xm: List[str]) -> Tuple[str, str]:
    """
    Pick (delim, esc) deterministically from X_m using folding degeneracy as a rarity proxy:
      - delim: argmin_w g_m(w), tie-break by lexicographic w
      - esc: next argmin distinct from delim
    """
    items = [(len(pre[w]), w) for w in Xm]
    items.sort(key=lambda x: (x[0], x[1]))
    if len(items) < 2:
        raise ValueError("Need at least 2 stable labels to select delimiter and escape")
    delim = items[0][1]
    esc = items[1][1] if items[1][1] != delim else items[2][1]
    if esc == delim:
        raise RuntimeError("Failed to choose distinct delim/esc")
    return str(delim), str(esc)


def _int_from_bits(bits: List[int]) -> int:
    x = 0
    for b in bits:
        x = (x << 1) | (int(b) & 1)
    return int(x)


def _bits_from_int(x: int, bit_length: int) -> List[int]:
    if bit_length < 0:
        raise ValueError("bit_length must be nonnegative")
    out = [0] * bit_length
    y = int(x)
    for i in range(bit_length - 1, -1, -1):
        out[i] = y & 1
        y >>= 1
    return out


def _bits_to_self_delim_int(bits: List[int]) -> int:
    """
    Self-delimiting encoding of a bitstring into a single positive integer:
      X = 2^L + value(bits), where L=len(bits).
    Then L can be recovered from floor(log2 X), and bits from X-2^L.

    This removes the need to transmit bit_length as side information.
    """
    L = len(bits)
    if L < 0:
        raise ValueError("invalid bit length")
    v = _int_from_bits(bits)
    return (1 << L) + int(v)


def _self_delim_int_to_bits(x: int) -> List[int]:
    """
    Inverse of _bits_to_self_delim_int.
    """
    X = int(x)
    if X <= 0:
        raise ValueError("self-delim integer must be positive")
    L = X.bit_length() - 1  # floor(log2 X)
    v = X - (1 << L)
    return _bits_from_int(int(v), bit_length=int(L))


def _to_base(x: int, base: int) -> List[int]:
    if base <= 1:
        raise ValueError("base must be >= 2")
    y = int(x)
    if y < 0:
        raise ValueError("x must be nonnegative")
    if y == 0:
        return [0]
    digits: List[int] = []
    while y > 0:
        digits.append(int(y % base))
        y //= base
    digits.reverse()
    return digits


def _from_base(digits: List[int], base: int) -> int:
    if base <= 1:
        raise ValueError("base must be >= 2")
    y = 0
    for d in digits:
        if d < 0 or d >= base:
            raise ValueError("digit out of range")
        y = y * base + int(d)
    return int(y)


def bits_to_allowed_micro_indices(bits: List[int], allowed: List[int]) -> List[int]:
    """
    Encode a bitstring into a sequence of microstates restricted to a finite allowed set.

    This is an invertible base conversion:
      bits -> self-delim integer -> base-|allowed| digits -> microstates.
    """
    if not allowed:
        raise ValueError("allowed set must be nonempty")
    base = len(allowed)
    x = _bits_to_self_delim_int(bits)
    digits = _to_base(x, base=base)
    return [int(allowed[d]) for d in digits]


def allowed_micro_indices_to_bits(symbols: List[int], allowed: List[int]) -> List[int]:
    """
    Invert bits_to_allowed_micro_indices.
    """
    if not allowed:
        raise ValueError("allowed set must be nonempty")
    base = len(allowed)
    pos = {int(v): i for i, v in enumerate(allowed)}
    digits: List[int] = []
    for s in symbols:
        if int(s) not in pos:
            raise ValueError("symbol not in allowed set")
        digits.append(int(pos[int(s)]))
    x = _from_base(digits, base=base)
    return _self_delim_int_to_bits(int(x))


def _count_trailing_tokens(stream: List[str], token: str) -> int:
    k = 0
    for w in reversed(stream):
        if w != token:
            break
        k += 1
    return int(k)


def absorb(st: BHState, micro: int) -> None:
    """
    Absorb one input microstate into the black hole:
    - enqueue N in {0,..,2^m-1}
    - increase mass by 1 (energy added)
    """
    if micro < 0 or micro >= (1 << st.m):
        raise ValueError("micro must be in {0,..,2^m-1}.")
    st.q.append(micro)
    st.mass += 1


def forward_simulate_single_stream(
    base_vacuum_mass: int, m: int, message_micro: List[int]
) -> Tuple[BHState, List[str], Dict[str, int]]:
    """
    Single-stream schedule:
      1) Absorb the entire message (each microstate increases mass by 1).
      2) Radiate for total ticks T = (base_vacuum_mass + L*t) + L, where:
           L = len(message_micro)
           t = digits_per_fiber (base-|X_m| digits to encode any fiber coordinate).
         The initial mass is set to base_vacuum_mass + L*t so there is enough
         budget to release all stashed fiber coordinates (late radiation) and then
         emit base_vacuum_mass vacuum symbols.

    Returns:
      - final internal state (mass=0, empty queue, empty stash)
      - radiation stream: a list of stable labels w in X_m (only)
      - metadata dict with keys: L, t, base_vacuum_mass
    """
    Xm = all_xm(m)
    pre = fiber_preimages(m)
    # Choose delimiter/escape symbols from X_m based on rarity proxy (small g_m).
    delim, esc = _select_delim_esc(pre, Xm)
    digit_alphabet = [w for w in Xm if w not in (delim, esc)]
    B = len(digit_alphabet)
    if B <= 1:
        raise RuntimeError("digit_alphabet too small after reserving delimiter/escape")

    # Digits per fiber are computed in base B, so digit stream avoids delim/esc by construction.
    g_max = max(len(v) for v in pre.values()) if pre else 1
    t = _digits_per_fiber(m, pre, digit_alphabet)

    L = len(message_micro)
    if int(base_vacuum_mass) < 2:
        raise ValueError("base_vacuum_mass must be >= 2 for delimiter-based decoding")
    # We will emit: (L + L*t) + base_vacuum_mass symbols after absorption.
    # Escaping may add extra radiation ticks; we include them below after constructing the stream.
    initial_mass = int(base_vacuum_mass) + int(L) * int(t)

    st = BHState(mass=initial_mass, m=m, q=[], stash_j=[])
    for x in message_micro:
        absorb(st, x)

    # Materialize the full stash-digit stream deterministically (after absorption).
    A = len(Xm)
    stash_digits: List[int] = []
    # We cannot compute stash_j until we emit the coarse labels; do that first deterministically.
    coarse_out: List[str] = []
    for _ in range(L):
        if st.mass <= 0:
            raise RuntimeError("mass exhausted during coarse emission")
        n = st.q.pop(0)
        w = fold_m(n, m)
        fiber = pre[w]
        try:
            j = fiber.index(n)
        except ValueError as e:
            raise RuntimeError("Internal inconsistency: n not found in its own Fold_m fiber") from e
        st.stash_j.append(int(j))
        st.mass -= 1
        coarse_out.append(w)

    # Encode all stashed j into base-A digits (FIFO).
    if t > 0:
        cap = 1
        for _ in range(t):
            cap *= B
        for j in st.stash_j:
            if j >= cap:
                raise RuntimeError("fiber coordinate does not fit into declared digit width")
            stash_digits.extend(_encode_base_A(int(j), A=B, t=t))

    # Prepare recovery symbols as stable labels.
    digit_out: List[str] = [digit_alphabet[int(d)] for d in stash_digits]
    # Clear stash (digits are now represented in the external record to be scheduled).
    st.stash_j.clear()

    # Interleave payload and recovery into a single record stream (non-vacuum).
    # Select mixing parameters from a finite family. For self-description, we will include
    # these parameters in the emitted header.
    # To avoid circularity, the selection uses only (L,t,A) via a maximally conservative ambiguity model.
    g_list_max = [int(A**t) if t > 0 else 1 for _ in range(L)]
    params = _cap_select_mixing_params(L=L, t=t, g_list=g_list_max, A=A)
    scramble_delay = int(params["scramble_delay"])
    exponent = int(params["exponent"])
    schedule = _interleave_schedule(L=L, t=t, scramble_delay=scramble_delay, exponent=exponent)
    if len(schedule) != (L + (L * t)):
        raise RuntimeError("Schedule length mismatch")
    mixed_nonvac: List[str] = []
    p_i = 0
    r_i = 0
    for tag in schedule:
        if tag == "P":
            mixed_nonvac.append(coarse_out[p_i])
            p_i += 1
        else:
            mixed_nonvac.append(digit_out[r_i])
            r_i += 1
    if p_i != L or r_i != (L * t):
        raise RuntimeError("Interleaving indices mismatch")

    # Delimiter framing:
    # If the non-vacuum stream contains delim/esc, apply escaping; otherwise keep it raw.
    # Escaping appends an esc terminator so the decoder can detect it unambiguously.
    needs_escape = any((w == delim or w == esc) for w in mixed_nonvac)
    if needs_escape:
        escaped_nonvac = _escape_stream(mixed_nonvac, delim=delim, esc=esc)
        escape_extra = len(escaped_nonvac) - len(mixed_nonvac)
        if escape_extra < 0:
            raise RuntimeError("escape length bookkeeping error")
        # Escaping overhead adds extra radiation ticks; include it in the baseline mass budget.
        st.mass += int(escape_extra)
    else:
        escaped_nonvac = mixed_nonvac
        escape_extra = 0

    # Account for recovery emissions in the mass ledger.
    # We already decremented mass for the L payload emissions during coarse emission above.
    # Each recovery symbol is also a radiation tick and must consume 1 unit of mass.
    if len(digit_out) > st.mass:
        raise RuntimeError("mass exhausted during recovery emission accounting")
    st.mass -= len(digit_out)

    # Account for escaping overhead ticks (if any).
    if int(escape_extra) > 0:
        if int(escape_extra) > st.mass:
            raise RuntimeError("mass exhausted during escaping overhead accounting")
        st.mass -= int(escape_extra)

    # Emit vacuum padding.
    vac_out: List[str] = []
    for _ in range(int(base_vacuum_mass)):
        if st.mass <= 0:
            raise RuntimeError("mass exhausted during vacuum emission")
        vac_out.append(delim)
        st.mass -= 1

    if st.mass != 0:
        raise RuntimeError("Invariant violated: mass should return to 0 after scheduled radiation ticks")
    if st.q:
        raise RuntimeError("Invariant violated: queue should be empty after scheduled radiation ticks")
    if st.stash_j:
        raise RuntimeError("Invariant violated: stash should be empty after scheduled radiation ticks")

    meta = {
        "L": int(L),
        "t": int(t),
        "base_vacuum_mass": int(base_vacuum_mass),
        "scramble_delay": int(scramble_delay),
        "exponent": int(exponent),
        "delim": str(delim),
        "esc": str(esc),
        "digit_base": int(B),
        "escape_extra": int(escape_extra),
        "needs_escape": bool(needs_escape),
    }
    return st, (escaped_nonvac + vac_out), meta


def recover_message_from_single_stream(
    radiation_w: List[str], m: int, meta: Dict[str, int]
) -> List[int]:
    """
    Exact inversion of forward_simulate_single_stream:
      - parse the radiation stream into:
          * coarse labels (length L)
          * digit stream (length L*t), grouped into t-digit fiber coordinates
          * vacuum padding (length base_vacuum_mass), checked against Fold_m(0)
      - reconstruct microstates using (w_i, j_i) via Fold_m fibers
    """
    pre = fiber_preimages(m)
    Xm = all_xm(m)
    A = len(Xm)
    w_to_digit = {w: i for i, w in enumerate(Xm)}

    # Fully headerless decoding:
    # Detect the delimiter tail as a maximal suffix of a rare delim in X_m, requiring length >= 2.
    # The escaped payload never contains a raw delim, and always ends with an esc terminator.
    delim, esc = _select_delim_esc(pre, Xm)
    digit_alphabet = [w for w in Xm if w not in (delim, esc)]
    B = len(digit_alphabet)
    if B <= 1:
        raise RuntimeError("digit_alphabet too small after reserving delimiter/escape")

    vac_len = _count_trailing_tokens(radiation_w, token=delim)
    if vac_len < 2:
        raise RuntimeError("No detectable vacuum tail (need >=2 delimiter tokens)")
    base_vacuum_mass = int(vac_len)

    # Infer t from the protocol (m and Fold_m fibers).
    t = _digits_per_fiber(m, pre, digit_alphabet)
    escaped_nonvac = radiation_w[: len(radiation_w) - base_vacuum_mass]
    # If escaping is used, the escaped payload ends with an esc terminator.
    # Under the "legal absorption" restriction, esc never appears in the non-vacuum record,
    # so we can treat a trailing esc as an unambiguous escaping marker.
    if escaped_nonvac and escaped_nonvac[-1] == esc:
        nonvac = _unescape_stream(escaped_nonvac, delim=delim, esc=esc)
    else:
        if any(w == esc for w in escaped_nonvac):
            raise RuntimeError("Found esc token in non-vacuum record without terminator; inconsistent encoding")
        nonvac = list(escaped_nonvac)

    nonvac_len = len(nonvac)
    denom = 1 + int(t)
    if denom <= 0 or (nonvac_len % denom) != 0:
        raise ValueError("record length incompatible with a headerless (L + L*t) non-vacuum structure")
    L = nonvac_len // denom

    # Recompute mixing parameters deterministically from the same finite family.
    g_list_max = [int(A**t) if t > 0 else 1 for _ in range(int(L))]
    params = _cap_select_mixing_params(L=int(L), t=int(t), g_list=g_list_max, A=A)
    scramble_delay = int(params["scramble_delay"])
    exponent = int(params["exponent"])

    schedule = _interleave_schedule(L=L, t=t, scramble_delay=scramble_delay, exponent=exponent)
    coarse, digit_stream = _split_by_schedule(nonvac, schedule)

    # Decode fiber coordinates.
    js: List[int] = []
    if t == 0:
        js = [0] * L
    else:
        if len(digit_stream) != L * t:
            raise RuntimeError("Digit stream length mismatch")
        for i in range(L):
            block = digit_stream[i * t : (i + 1) * t]
            # Decode base-B digits using digit_alphabet.
            dmap = {w: idx for idx, w in enumerate(digit_alphabet)}
            digits = [int(dmap[w]) for w in block]
            js.append(_decode_base_A(digits, A=B))

    recovered_micro: List[int] = []
    for w, j in zip(coarse, js):
        fiber = pre.get(w)
        if fiber is None:
            raise RuntimeError("Coarse symbol w is not in the Fold_m image")
        if j < 0 or j >= len(fiber):
            raise RuntimeError("Decoded fiber coordinate out of range for its coarse stable label")
        recovered_micro.append(int(fiber[int(j)]))

    return recovered_micro


def _bits_from_ascii(s: str) -> List[int]:
    out: List[int] = []
    for ch in s.encode("utf-8"):
        for i in range(8):
            out.append((ch >> (7 - i)) & 1)
    return out


def _bits_to_ascii(bits: List[int]) -> str:
    if len(bits) % 8 != 0:
        raise ValueError("bit length must be multiple of 8 to decode utf-8 bytes")
    data = bytearray()
    for i in range(0, len(bits), 8):
        b = 0
        for j in range(8):
            b = (b << 1) | (bits[i + j] & 1)
        data.append(b)
    return data.decode("utf-8", errors="replace")


def _allowed_set_by_mode(m: int, mode: str) -> Tuple[List[int], Dict[str, str]]:
    """
    Build an allowed absorption set of microstates (dyadic indices) under a declared mode.

    Modes:
      - "unrestricted": all microstates are allowed.
      - "avoid_delim_esc": only microstates with Fold_m(N) not in {delim, esc} are allowed.
      - "cyclic_only": only microstates with Fold_m(N) in X_m^cyc and not in {delim, esc} are allowed.
      - "boundary_only": only microstates with Fold_m(N) in X_m^bdry and not in {delim, esc} are allowed.
    """
    pre = fiber_preimages(m)
    Xm = all_xm(m)
    delim, esc = _select_delim_esc(pre, Xm)
    cyc, bdry = split_cyc_bdry(Xm)

    allowed: List[int] = []
    if mode == "unrestricted":
        allowed = list(range(1 << m))
    elif mode == "avoid_delim_esc":
        for w in Xm:
            if w in (delim, esc):
                continue
            allowed.extend(pre[w])
    elif mode == "cyclic_only":
        for w in cyc:
            if w in (delim, esc):
                continue
            allowed.extend(pre[w])
    elif mode == "boundary_only":
        for w in bdry:
            if w in (delim, esc):
                continue
            allowed.extend(pre[w])
    else:
        raise ValueError("unknown absorption mode")

    allowed = sorted(set(int(x) for x in allowed))
    info = {
        "delim": delim,
        "esc": esc,
        "mode": mode,
        "Xm_card": str(len(Xm)),
        "cyc_card": str(len(cyc)),
        "bdry_card": str(len(bdry)),
        "allowed_card": str(len(allowed)),
    }
    return allowed, info


def _run_case(m: int, base_vacuum_mass: int, msg_text: str, mode: str) -> Dict[str, str]:
    bits = _bits_from_ascii(msg_text)
    allowed, info = _allowed_set_by_mode(m, mode=mode)
    msg_micro = bits_to_allowed_micro_indices(bits, allowed=allowed)
    _, radiation_w, meta = forward_simulate_single_stream(
        base_vacuum_mass=base_vacuum_mass, m=m, message_micro=msg_micro
    )
    recovered_micro = recover_message_from_single_stream(radiation_w=radiation_w, m=m, meta={})
    recovered_bits = allowed_micro_indices_to_bits(recovered_micro, allowed=allowed)
    recovered_text = _bits_to_ascii(recovered_bits)
    ok = recovered_text == msg_text

    out = {
        "mode": mode,
        "ok": "1" if ok else "0",
        "allowed_card": info["allowed_card"],
        "delim": info["delim"],
        "esc": info["esc"],
        "t": str(meta["t"]),
        "digit_base": str(meta["digit_base"]),
        "needs_escape": "1" if meta["needs_escape"] else "0",
        "escape_extra": str(meta["escape_extra"]),
        "radiation_ticks": str(len(radiation_w)),
        "payload": str(meta["L"]),
        "recovery": str(meta["L"] * meta["t"]),
        "vacuum": str(meta["base_vacuum_mass"]),
    }
    return out


def bits_to_micro_indices(bits: List[int], m: int) -> Tuple[List[int], int]:
    """
    Pack a bitstring into base-2^m symbols (microstates in {0,..,2^m-1}).
    Returns (symbols, original_bit_length).
    """
    if m <= 0:
        raise ValueError("m must be positive")
    L = len(bits)
    pad = (-L) % m
    bits2 = bits + [0] * pad
    out: List[int] = []
    for i in range(0, len(bits2), m):
        x = 0
        for j in range(m):
            x = (x << 1) | (bits2[i + j] & 1)
        out.append(x)
    return out, L


def micro_indices_to_bits(symbols: List[int], m: int, bit_length: int) -> List[int]:
    """
    Unpack base-2^m symbols back into bits and truncate to bit_length.
    """
    if m <= 0:
        raise ValueError("m must be positive")
    out: List[int] = []
    for x in symbols:
        if x < 0 or x >= (1 << m):
            raise ValueError("symbol out of range for m")
        for j in range(m):
            out.append((x >> (m - 1 - j)) & 1)
    return out[:bit_length]


def main() -> None:
    m = 6  # anchor resolution in the paper
    base_vacuum_mass = 64  # baseline service budget (vacuum padding emitted after recovery)
    msg_text = "TICK-INFORMATION"
    msg_bits = _bits_from_ascii(msg_text)
    # Default demonstration mode: avoid_delim_esc (legal absorption).
    allowed, info = _allowed_set_by_mode(m, mode="avoid_delim_esc")
    msg_micro = bits_to_allowed_micro_indices(msg_bits, allowed=allowed)

    final_state, radiation_w, meta = forward_simulate_single_stream(
        base_vacuum_mass=base_vacuum_mass, m=m, message_micro=msg_micro
    )
    # Recover without any meta (delimiter tail + escaping make the record self-delimiting).
    recovered_micro = recover_message_from_single_stream(radiation_w=radiation_w, m=m, meta={})
    recovered_bits = allowed_micro_indices_to_bits(recovered_micro, allowed=allowed)
    recovered_text = _bits_to_ascii(recovered_bits)

    ok = recovered_micro == msg_micro and recovered_text == msg_text

    Xm = all_xm(m)
    cyc, bdry = split_cyc_bdry(Xm)
    print("=== Black-hole-equivalent queue model (deterministic) ===")
    print(f"m: {m}")
    print(f"|X_m|: {len(Xm)}; |X_m^cyc|: {len(cyc)}; |X_m^bdry|: {len(bdry)}")
    print(f"base_vacuum_mass: {base_vacuum_mass}")
    print(f"digits_per_fiber (t): {meta['t']}")
    print(f"scramble_delay: {meta['scramble_delay']}")
    print(f"mix_exponent: {meta['exponent']}")
    print(f"message: {msg_text!r}")
    print(f"message_bits: {len(msg_bits)} bits")
    print(f"message_micro: {len(msg_micro)} symbols in [0,2^{m})")
    print(f"radiation_ticks: {len(radiation_w)} records (each is w in X_m)")
    print(f"  payload emissions: {meta['L']}")
    print(f"  recovery emissions: {meta['L'] * meta['t']}")
    print(f"  vacuum ticks: {meta['base_vacuum_mass']}")
    print(f"  escape_extra ticks: {meta['escape_extra']}")
    print(f"recovered: {recovered_text!r}")
    print(f"recovery_ok: {ok}")
    if not ok:
        raise SystemExit(2)

    # Page-surrogate audit diagnostic: remaining ambiguity under the internal schedule.
    # This is printed only as an internal audit; it is not part of the "outside" observable.
    pre = fiber_preimages(m)
    g_list = [len(pre[fold_m(n, m)]) for n in msg_micro]
    A = len(Xm)
    t = int(meta["t"])
    sched = _interleave_schedule(
        L=int(meta["L"]),
        t=t,
        scramble_delay=int(meta["scramble_delay"]),
        exponent=int(meta["exponent"]),
    )
    nonvac_len = int(meta["L"]) + int(meta["L"]) * t
    sample = [0, nonvac_len // 4, nonvac_len // 2, (3 * nonvac_len) // 4, nonvac_len]
    sample = sorted(set(sample))
    print("=== Page-surrogate diagnostic (internal audit; U=remaining ambiguity bits) ===")
    for tick in sample:
        p_emit = 0
        r_emit = 0
        for tag in sched[: int(tick)]:
            if tag == "P":
                p_emit += 1
            else:
                r_emit += 1
        U = _remaining_ambiguity_bits(
            g_list=g_list,
            A=A,
            t=t,
            payload_emitted=p_emit,
            recovery_emitted=r_emit,
        )
        print(f"tick={tick:4d} payload={p_emit:3d} recovery={r_emit:3d} U_bits={U:.6f}")

    # Sweep a small set of absorption modes and report key diagnostics.
    print("=== Absorption-mode sweep (summary) ===")
    modes = ["unrestricted", "avoid_delim_esc", "cyclic_only", "boundary_only"]
    for mode in modes:
        row = _run_case(m=m, base_vacuum_mass=base_vacuum_mass, msg_text=msg_text, mode=mode)
        print(
            " ".join(
                [
                    f"mode={row['mode']}",
                    f"ok={row['ok']}",
                    f"allowed={row['allowed_card']}",
                    f"t={row['t']}",
                    f"B={row['digit_base']}",
                    f"escape={row['needs_escape']}/{row['escape_extra']}",
                    f"ticks={row['radiation_ticks']}",
                ]
            )
        )


if __name__ == "__main__":
    main()

