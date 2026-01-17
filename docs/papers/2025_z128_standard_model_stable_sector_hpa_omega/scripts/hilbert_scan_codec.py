# -*- coding: utf-8 -*-
"""
Hilbert scan codec (variable m with gate words) for the HPA interface figures.

This implements a *stream-level* encoder/decoder with a simple gate-driven state machine:

- Base mode: read fixed-length words of length m_base (default 6).
- Uplift gate: upon seeing the uplift word (default "101001") in base mode,
  switch so that the *next* token is read with length m_hi (default 8).
- High mode: read fixed-length words of length m_hi.
- Downlift gate: while in high mode, if a token's prefix matches the downlift pattern,
  switch back so that the *next* token is read with length m_base.
- Frame boundary: a frame starts at the first token equal to start_end (default "100001")
  and ends when this token appears again (inclusive).

Zeckendorf admissibility in this repo means *forbidden substring "11"*.
We enforce:
  - each token is individually admissible ("11" not in token),
  - the concatenated bitstream is admissible (no "11" across token boundaries).

The codec is deterministic and pure-Python.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


def is_zeckendorf_admissible(bits: str) -> bool:
    bits = str(bits)
    if any(c not in "01" for c in bits):
        return False
    return "11" not in bits


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


@dataclass(frozen=True)
class GateSpec:
    start_end: str = "100001"
    uplift: str = "101001"
    # Downlift is detected in *high* mode by matching a prefix.
    # Default uses the 6-bit downlift gate "100101" (and allows any high-mode suffix).
    downlift_prefix: str = "100101"


@dataclass(frozen=True)
class CodecSpec:
    m_base: int = 6
    m_hi: int = 8
    gates: GateSpec = GateSpec()

    def __post_init__(self) -> None:
        _require(self.m_base >= 1, "m_base must be >= 1")
        _require(self.m_hi >= self.m_base, "m_hi must be >= m_base")
        _require(len(self.gates.start_end) == self.m_base, "start_end must be length m_base")
        _require(len(self.gates.uplift) == self.m_base, "uplift must be length m_base")
        _require(1 <= len(self.gates.downlift_prefix) <= self.m_hi, "downlift_prefix length must be in [1, m_hi]")
        _require(is_zeckendorf_admissible(self.gates.start_end), "start_end must be Zeckendorf-admissible")
        _require(is_zeckendorf_admissible(self.gates.uplift), "uplift must be Zeckendorf-admissible")
        _require(is_zeckendorf_admissible(self.gates.downlift_prefix), "downlift_prefix must be Zeckendorf-admissible")


class HilbertGateCodec:
    """
    Encoder/decoder for the variable-m Hilbert scan stream (tokenized by the gate state machine).
    """

    def __init__(self, spec: CodecSpec = CodecSpec()) -> None:
        self.spec = spec

    def validate_tokens(self, tokens: Sequence[str]) -> None:
        """
        Validate a token sequence against:
          - schedule lengths implied by the gate state machine,
          - per-token admissibility,
          - global admissibility of the concatenation,
          - frame boundary (start_end appears at least twice: start+end).
        """
        _require(len(tokens) >= 2, "Need at least two tokens (start and end).")

        m = int(self.spec.m_base)
        seen_start = 0
        prev_last: Optional[str] = None
        for i, tok in enumerate(tokens):
            tok = str(tok)
            _require(len(tok) == m, f"Token {i} length mismatch: expected {m}, got {len(tok)}.")
            _require(is_zeckendorf_admissible(tok), f"Token {i} not Zeckendorf-admissible: {tok!r}")
            if prev_last is not None:
                _require(
                    not (prev_last == "1" and tok[0] == "1"),
                    f"Concatenation violates Zeckendorf at boundary between token {i-1} and {i}.",
                )
            prev_last = tok[-1]

            if m == self.spec.m_base:
                if tok == self.spec.gates.start_end:
                    seen_start += 1
                if tok == self.spec.gates.uplift:
                    m = int(self.spec.m_hi)  # next token length
            else:
                # high mode: downlift detected by prefix match
                if tok.startswith(self.spec.gates.downlift_prefix):
                    m = int(self.spec.m_base)  # next token length

        _require(seen_start >= 2, f"Need start_end token {self.spec.gates.start_end!r} at least twice (start+end).")

    def encode(self, tokens: Sequence[str]) -> str:
        """
        Encode tokens to a single bitstream string (after validation).
        """
        self.validate_tokens(tokens)
        return "".join(str(t) for t in tokens)

    def decode(self, bitstream: str) -> List[str]:
        """
        Decode a bitstream into tokens using the gate state machine.
        Stops at the second occurrence of start_end *in base mode* (inclusive).
        """
        s = str(bitstream).strip()
        _require(s != "", "Empty bitstream.")
        _require(all(c in "01" for c in s), "Bitstream must be a 0/1 string.")
        _require(is_zeckendorf_admissible(s), 'Bitstream violates Zeckendorf admissibility ("11" found).')

        tokens: List[str] = []
        m = int(self.spec.m_base)
        i = 0
        seen_start = 0
        while i < len(s):
            _require(i + m <= len(s), f"Truncated bitstream: need {m} bits at position {i}.")
            tok = s[i : i + m]
            tokens.append(tok)
            i += m

            if m == self.spec.m_base:
                if tok == self.spec.gates.start_end:
                    seen_start += 1
                    if seen_start >= 2:
                        break
                if tok == self.spec.gates.uplift:
                    m = int(self.spec.m_hi)
            else:
                if tok.startswith(self.spec.gates.downlift_prefix):
                    m = int(self.spec.m_base)

        # Validate reconstructed schedule; also ensures we ended on an actual frame boundary.
        _require(i == len(s), "Trailing bits after end-of-frame marker (bitstream contains extra data).")
        self.validate_tokens(tokens)
        return tokens


def hilbert_path_2d(*, n_bits: int = 3) -> List[Tuple[int, int]]:
    """
    Convenience: use the repo's canonical 2D Hilbert curve implementation.
    Returns a list of (x,y) coords of length 4^n_bits.
    """
    # Local import: keep codec standalone for unit tests and avoid heavyweight imports by default.
    import exp_hilbert_chirality_index as hil  # type: ignore

    path = hil.hilbert_curve(int(n_bits))
    return [(int(x), int(y)) for (x, y) in path]


# -------------------------
# Self-describing stream codec (arbitrary uplifts/downs, no out-of-band schedule)
# -------------------------


FIB_WEIGHTS_6 = [1, 2, 3, 5, 8, 13]  # [F2..F7] with F1=F2=1


def zeckendorf_value6(w: str) -> int:
    w = str(w)
    _require(len(w) == 6, "zeckendorf_value6 requires a 6-bit word.")
    _require(all(c in "01" for c in w), "Word must be a 0/1 string.")
    _require(is_zeckendorf_admissible(w), 'Word violates Zeckendorf admissibility ("11").')
    return sum(int(bit) * FIB_WEIGHTS_6[i] for i, bit in enumerate(w))


def zeckendorf_word6(n: int) -> str:
    """
    Canonical Zeckendorf (no-adjacent-ones) digits over weights [1,2,3,5,8,13],
    padded/truncated to 6 bits.
    """
    n = int(n)
    _require(0 <= n <= sum(FIB_WEIGHTS_6), "n out of representable range for 6-bit Zeckendorf payload.")
    digits = [0] * 6
    # Greedy on descending weights with skip-next constraint.
    i = 5
    while n > 0 and i >= 0:
        if FIB_WEIGHTS_6[i] <= n:
            digits[i] = 1
            n -= FIB_WEIGHTS_6[i]
            i -= 2
        else:
            i -= 1
    w = "".join("1" if b else "0" for b in digits[:6])
    _require(is_zeckendorf_admissible(w), "Internal error: payload word not admissible.")
    return w


@dataclass(frozen=True)
class SelfCodecSpec:
    """
    Self-describing variable-m codec:
    - frame boundary uses start_end in base mode (m_base)
    - uplift record: uplift (m_base) + payload (m_base) -> set m := V(payload)
    - downlift record: downlift_marker(m_current) + payload (m_base) -> set m := V(payload)
      where downlift_marker(m) = downlift_prefix + "0"*(m-m_base) for m>m_base, and equals downlift_prefix for m=m_base.
    """

    m_base: int = 6
    gates: GateSpec = GateSpec(downlift_prefix="100101")
    # Hilbert-wiring discipline after an uplift (m increases):
    # require at least f(m) *data tokens* at the new m before any further control records.
    #
    # Policies:
    # - "fixed": f(m)=min_data_tokens_after_uplift
    # - "microblock": f(m)=2^(m-6) (complete 2D microblock at resolution uplift from m=6 anchor)
    uplift_min_tokens_policy: str = "microblock"
    min_data_tokens_after_uplift: int = 1

    def __post_init__(self) -> None:
        _require(self.m_base == 6, "This self-describing codec currently fixes m_base=6 (payload is 6-bit Zeckendorf).")
        _require(self.gates.downlift_prefix == "100101", "Downlift prefix must be the 6-bit gate word 100101.")
        pol = str(self.uplift_min_tokens_policy)
        _require(pol in {"fixed", "microblock"}, 'uplift_min_tokens_policy must be "fixed" or "microblock".')
        _require(int(self.min_data_tokens_after_uplift) >= 0, "min_data_tokens_after_uplift must be >= 0.")


class SelfDescribingHilbertCodec:
    """
    A stream codec where the Zeckendorf-admissible bitstream itself carries all control information.
    No external schedule is needed: m-changes are logged in-stream as gate+payload records.
    """

    def __init__(self, spec: SelfCodecSpec = SelfCodecSpec()) -> None:
        self.spec = spec

    def _downlift_marker_for_m(self, m: int) -> str:
        m = int(m)
        _require(m >= 6, "m must be >= 6.")
        if m == 6:
            return self.spec.gates.downlift_prefix
        return self.spec.gates.downlift_prefix + ("0" * (m - 6))

    def _payload_to_m(self, payload6: str) -> int:
        v = int(zeckendorf_value6(payload6))
        # No "extra" restriction beyond what the 6-bit payload itself can carry.
        # Intrinsic bound: V(payload6) ∈ [0, 32]. Protocol bound: require m >= 6.
        _require(v >= 6, f"Payload sets m={v}, but m must be >= 6.")
        return int(v)

    def _min_data_tokens_after_uplift(self, new_m: int) -> int:
        new_m = int(new_m)
        if self.spec.uplift_min_tokens_policy == "fixed":
            return int(self.spec.min_data_tokens_after_uplift)
        # "microblock": complete 2D microblock under uplift from m=6 anchor.
        # m=6 -> 1 cell; m -> 2^(m-6) subcells in 2D (since each +2 bits quarters area).
        if new_m <= 6:
            return 0
        return int(1 << (new_m - 6))

    def validate_tokens(self, tokens: Sequence[str]) -> None:
        """
        Validate a variable-length token sequence against the self-describing FSM:
        - token lengths follow the current m, except that after a control marker we read a 6-bit payload.
        - per-token admissibility and global no-'11' boundary admissibility.
        - frame boundary must be closed (start_end appears at least twice in base mode).
        """
        _require(len(tokens) >= 2, "Need at least two tokens.")

        cur_m = 6
        expect_payload = False
        seen_start = 0
        prev_last: Optional[str] = None
        need_data_after_uplift = 0
        pending_prev_m: Optional[int] = None

        for i, tok0 in enumerate(tokens):
            tok = str(tok0)
            expected_len = 6 if expect_payload else cur_m
            _require(len(tok) == expected_len, f"Token {i} length mismatch: expected {expected_len}, got {len(tok)}.")
            _require(is_zeckendorf_admissible(tok), f"Token {i} not Zeckendorf-admissible: {tok!r}")
            if prev_last is not None:
                _require(
                    not (prev_last == "1" and tok[0] == "1"),
                    f"Concatenation violates Zeckendorf at boundary between token {i-1} and {i}.",
                )
            prev_last = tok[-1]

            if expect_payload:
                # Apply the previously requested mode change.
                prev_m = int(pending_prev_m) if pending_prev_m is not None else int(cur_m)
                new_m = self._payload_to_m(tok)
                cur_m = int(new_m)
                if int(new_m) > int(prev_m):
                    need_data_after_uplift = self._min_data_tokens_after_uplift(int(new_m))
                expect_payload = False
                pending_prev_m = None
                continue

            # Normal token processing at cur_m.
            if cur_m == 6 and tok == self.spec.gates.start_end:
                seen_start += 1

            # Enforce "no immediate control after uplift" until enough data tokens are emitted.
            if need_data_after_uplift > 0:
                is_control = False
                if cur_m == 6 and tok == self.spec.gates.uplift:
                    is_control = True
                # Downlift control markers are only recognized in high mode (cur_m > 6).
                if cur_m > 6 and tok == self._downlift_marker_for_m(cur_m):
                    is_control = True
                _require(not is_control, "Control record encountered immediately after uplift; need data tokens to traverse refined wiring.")
                need_data_after_uplift -= 1

            if cur_m == 6 and tok == self.spec.gates.uplift:
                # Uplift record: next 6-bit payload selects new m.
                expect_payload = True
                pending_prev_m = int(cur_m)
                continue

            # Downlift records are only interpreted in high mode.
            if cur_m > 6 and tok == self._downlift_marker_for_m(cur_m):
                # Downlift record: next 6-bit payload selects new m (not necessarily 6).
                expect_payload = True
                pending_prev_m = int(cur_m)
                continue

        _require(not expect_payload, "Stream ended while expecting an m-change payload token.")
        _require(seen_start >= 2, f"Need start_end token {self.spec.gates.start_end!r} at least twice (start+end).")

    def encode(self, tokens: Sequence[str]) -> str:
        self.validate_tokens(tokens)
        return "".join(str(t) for t in tokens)

    def decode(self, bitstream: str) -> List[str]:
        s = str(bitstream).strip()
        _require(s != "", "Empty bitstream.")
        _require(all(c in "01" for c in s), "Bitstream must be a 0/1 string.")
        _require(is_zeckendorf_admissible(s), 'Bitstream violates Zeckendorf admissibility ("11" found).')

        tokens: List[str] = []
        cur_m = 6
        expect_payload = False
        i = 0
        seen_start = 0
        need_data_after_uplift = 0
        pending_prev_m: Optional[int] = None

        while i < len(s):
            take = 6 if expect_payload else cur_m
            _require(i + take <= len(s), f"Truncated bitstream: need {take} bits at position {i}.")
            tok = s[i : i + take]
            tokens.append(tok)
            i += take

            if expect_payload:
                prev_m = int(pending_prev_m) if pending_prev_m is not None else int(cur_m)
                new_m = self._payload_to_m(tok)
                cur_m = int(new_m)
                if int(new_m) > int(prev_m):
                    need_data_after_uplift = self._min_data_tokens_after_uplift(int(new_m))
                expect_payload = False
                pending_prev_m = None
                continue

            if cur_m == 6 and tok == self.spec.gates.start_end:
                seen_start += 1
                if seen_start >= 2:
                    break

            if need_data_after_uplift > 0:
                is_control = False
                if cur_m == 6 and tok == self.spec.gates.uplift:
                    is_control = True
                if cur_m > 6 and tok == self._downlift_marker_for_m(cur_m):
                    is_control = True
                _require(not is_control, "Control record encountered immediately after uplift; need data tokens to traverse refined wiring.")
                need_data_after_uplift -= 1

            if cur_m == 6 and tok == self.spec.gates.uplift:
                expect_payload = True
                pending_prev_m = int(cur_m)
                continue

            if cur_m > 6 and tok == self._downlift_marker_for_m(cur_m):
                expect_payload = True
                pending_prev_m = int(cur_m)
                continue

        _require(i == len(s), "Trailing bits after end-of-frame marker (bitstream contains extra data).")
        self.validate_tokens(tokens)
        return tokens

