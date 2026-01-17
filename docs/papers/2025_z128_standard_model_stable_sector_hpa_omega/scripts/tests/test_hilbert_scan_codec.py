# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
import unittest


# Allow importing from the scripts directory when running from repo root.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.abspath(os.path.join(THIS_DIR, ".."))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


from hilbert_scan_codec import (  # noqa: E402
    CodecSpec,
    GateSpec,
    HilbertGateCodec,
    SelfDescribingHilbertCodec,
    SelfCodecSpec,
    hilbert_path_2d,
    is_zeckendorf_admissible,
    zeckendorf_word6,
)


class TestZeckendorfAdmissibility(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertTrue(is_zeckendorf_admissible("0"))
        self.assertTrue(is_zeckendorf_admissible("1"))
        self.assertTrue(is_zeckendorf_admissible("101001"))
        self.assertTrue(is_zeckendorf_admissible("01001010"))
        self.assertFalse(is_zeckendorf_admissible("11"))
        self.assertFalse(is_zeckendorf_admissible("1011"))
        self.assertFalse(is_zeckendorf_admissible("10a01"))


class TestHilbertGateCodec(unittest.TestCase):
    def test_roundtrip_default(self) -> None:
        codec = HilbertGateCodec(CodecSpec(m_base=6, m_hi=8, gates=GateSpec()))
        tokens = [
            "100001",  # start
            "000000",
            "101001",  # uplift (next token is m=8)
            "01001010",
            "10010100",  # downlift by prefix "100101" (next token is m=6)
            "010010",
            "100001",  # end
        ]
        bitstream = codec.encode(tokens)
        self.assertEqual(codec.decode(bitstream), tokens)

    def test_invalid_cross_token_boundary(self) -> None:
        codec = HilbertGateCodec()
        # boundary violation: token0 ends with 1 and token1 starts with 1
        tokens = ["000001", "100000", "100001", "100001"]
        with self.assertRaises(ValueError):
            codec.encode(tokens)

    def test_invalid_length_schedule(self) -> None:
        codec = HilbertGateCodec()
        # after uplift, the next token must be length 8
        tokens = ["100001", "101001", "010010", "100001"]
        with self.assertRaises(ValueError):
            codec.encode(tokens)

    def test_decode_rejects_trailing_bits(self) -> None:
        codec = HilbertGateCodec()
        # Need a Zeckendorf-legal separation between start and end markers.
        tokens = ["100001", "000000", "100001"]
        s = codec.encode(tokens) + "0"
        with self.assertRaises(ValueError):
            codec.decode(s)

    def test_downlift_prefix_len6_gate(self) -> None:
        # Downlift is triggered by the 6-bit gate prefix "100101" (SU(3) boundary word).
        spec = CodecSpec(m_base=6, m_hi=8, gates=GateSpec(downlift_prefix="100101"))
        codec = HilbertGateCodec(spec)
        tokens = [
            "100001",
            "000000",
            "101001",  # uplift -> m=8
            "01001010",
            "10010100",  # startswith "100101" so downlift -> next is m=6
            "000000",
            "100001",
        ]
        bitstream = codec.encode(tokens)
        self.assertEqual(codec.decode(bitstream), tokens)


class TestHilbertPath(unittest.TestCase):
    def test_hilbert_path_neighbors(self) -> None:
        path = hilbert_path_2d(n_bits=3)
        self.assertEqual(len(path), 64)
        for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
            self.assertEqual(abs(x0 - x1) + abs(y0 - y1), 1)


class TestSelfDescribingHilbertCodec(unittest.TestCase):
    def test_roundtrip_multi_switch(self) -> None:
        # Arbitrary uplifts and downs are self-coded via gate+payload inside the Zeckendorf stream.
        codec = SelfDescribingHilbertCodec(SelfCodecSpec())
        p8 = zeckendorf_word6(8)
        p10 = zeckendorf_word6(10)
        p6 = zeckendorf_word6(6)

        # Downlift marker in m=8 is "100101" + "00" = "10010100"
        down8 = "10010100"

        tokens = [
            "100001",  # start (m=6)
            "000000",
            "101001",  # uplift record
            p8,  # payload sets m=8
            "01001010",  # some m=8 data
            down8,  # downlift record (in-stream marker at m=8)
            p10,  # payload sets m=10 (arbitrary switch)
            "0100101010",  # m=10 data (Zeckendorf-admissible)
            "1001010000",  # downlift marker in m=10 ("100101"+"0000")
            p6,  # payload sets m=6
            "000000",
            "100001",  # end (m=6)
        ]
        bitstream = codec.encode(tokens)
        self.assertEqual(codec.decode(bitstream), tokens)

    def test_rejects_payload_m_lt_6(self) -> None:
        codec = SelfDescribingHilbertCodec(SelfCodecSpec())
        p5 = zeckendorf_word6(5)  # protocol disallows m<6
        tokens = ["100001", "101001", p5, "000000", "100001"]
        with self.assertRaises(ValueError):
            codec.encode(tokens)

    def test_rejects_immediate_down_after_uplift(self) -> None:
        codec = SelfDescribingHilbertCodec(SelfCodecSpec(min_data_tokens_after_uplift=1))
        p8 = zeckendorf_word6(8)
        p6 = zeckendorf_word6(6)
        # Immediately after payload sets m=8, the next token is a control marker (downlift).
        tokens = [
            "100001",
            "000000",
            "101001",
            p8,  # sets m=8
            "10010100",  # downlift marker at m=8 (illegal here: must emit ≥1 data token at m=8 first)
            p6,
            "000000",
            "100001",
        ]
        with self.assertRaises(ValueError):
            codec.encode(tokens)


if __name__ == "__main__":
    unittest.main()

