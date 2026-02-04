#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified CLI for:
  1) Projection-word normalization (rewrite-to-normal-form + certificate trace)
  2) Fold_m collision-moment / Renyi-q fingerprint summaries

This file is intentionally small and composes existing, audited scripts in this
paper directory (instead of re-implementing math in a new codepath).

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_fragment(fragment: str, raw: Sequence[str], word: Optional[str]) -> Dict[str, Any]:
    """Return a standard normalized payload dict."""
    if fragment == "ze":
        import exp_pom_projword_ze_normalizer as ze

        raw2 = list(raw)
        if (not raw2) and (word is not None):
            raw2 = word.split()
        if not raw2:
            raise SystemExit("Empty word. Provide tokens or --word.")
        toks = ze.parse_tokens(raw2)
        nf = ze.normalize(toks)
        return {
            "fragment": fragment,
            "input": " ".join(str(t) for t in toks),
            "normal_form": " ".join(str(t) for t in nf),
            "rewrite_trace": [],
        }

    if fragment == "zepq":
        import exp_pom_projword_zepq_normalizer as zepq

        raw2 = list(raw)
        if (not raw2) and (word is not None):
            raw2 = word.split()
        if not raw2:
            raise SystemExit("Empty word. Provide tokens or --word.")
        toks = zepq.parse_tokens(raw2)
        nf = zepq.normalize(toks)
        return {
            "fragment": fragment,
            "input": " ".join(str(t) for t in toks),
            "normal_form": " ".join(str(t) for t in nf),
            "rewrite_trace": [],
        }

    if fragment == "liftproj":
        import exp_pom_projword_lift_proj_normalizer_demo as lp

        if word is None:
            word = " ".join(raw)
        if not word.strip():
            raise SystemExit("Empty word. Provide tokens or --word.")
        toks = lp.parse_word(word)
        nf, trace = lp.normalize(toks)
        return {
            "fragment": fragment,
            "input": lp.word_to_str(toks),
            "normal_form": lp.word_to_str(nf),
            "rewrite_trace": trace,
        }

    if fragment == "val":
        import exp_pom_rewriting_engine_demo as val

        if word is None:
            word = "; ".join(raw)
        if not word.strip():
            raise SystemExit("Empty word. Provide tokens or --word.")
        toks = val.parse_word(word)
        nf, trace = val.normalize(toks)
        return {
            "fragment": fragment,
            "input": val.word_to_str(toks),
            "normal_form": val.word_to_str(nf),
            "rewrite_trace": trace,
        }

    raise SystemExit(f"Unknown fragment {fragment!r}. Use one of: ze, zepq, liftproj, val.")


def cmd_normalize(args: argparse.Namespace) -> None:
    payload = _normalize_fragment(args.fragment, args.tokens, args.word)
    print(f"[pom-cli] fragment={payload['fragment']}", flush=True)
    print(f"[pom-cli] in:  {payload['input']}", flush=True)
    print(f"[pom-cli] nf:  {payload['normal_form']}", flush=True)
    if payload["rewrite_trace"]:
        print(f"[pom-cli] trace: {' '.join(payload['rewrite_trace'])}", flush=True)
    if args.json_out:
        _write_json(args.json_out, payload)
        print(f"[pom-cli] wrote {args.json_out}", flush=True)


def cmd_equiv(args: argparse.Namespace) -> None:
    if args.word1 is None or args.word2 is None:
        raise SystemExit("equiv requires --word1 and --word2.")

    if args.fragment in ("ze", "zepq"):
        p1 = _normalize_fragment(args.fragment, args.word1.split(), None)
        p2 = _normalize_fragment(args.fragment, args.word2.split(), None)
    else:
        p1 = _normalize_fragment(args.fragment, [], args.word1)
        p2 = _normalize_fragment(args.fragment, [], args.word2)
    eq = (p1["normal_form"] == p2["normal_form"])
    print(f"[pom-cli] fragment={args.fragment}", flush=True)
    print(f"[pom-cli] nf1: {p1['normal_form']}", flush=True)
    print(f"[pom-cli] nf2: {p2['normal_form']}", flush=True)
    print(f"[pom-cli] equivalent: {eq}", flush=True)
    raise SystemExit(0 if eq else 1)


@dataclass(frozen=True)
class RecRow:
    k: int
    order: int
    m0: int
    coeffs: List[int]


def _fold_rec_rows(k_max: int) -> List[RecRow]:
    import exp_fold_collision_moment_spectrum_k2_8 as k2_8
    import exp_fold_collision_moment_recursions_mod_dp as moddp

    rows: List[RecRow] = []
    for rec in k2_8.RECS:
        if rec.k <= k_max:
            rows.append(RecRow(k=rec.k, order=len(rec.coeffs), m0=int(rec.m0), coeffs=list(rec.coeffs)))
    for r in moddp.PRECOMPUTED_RECS_9_17:
        if int(r["k"]) <= k_max:
            rows.append(
                RecRow(
                    k=int(r["k"]),
                    order=int(r["order"]),
                    m0=int(r["m0"]),
                    coeffs=[int(c) for c in r["coeffs"]],
                )
            )
    rows.sort(key=lambda z: z.k)
    return rows


def cmd_fold_recs(args: argparse.Namespace) -> None:
    rows = _fold_rec_rows(k_max=int(args.k_max))
    payload = {"k_max": int(args.k_max), "rows": [r.__dict__ for r in rows]}
    for r in rows:
        coeffs = ", ".join(str(c) for c in r.coeffs)
        print(f"[pom-cli] k={r.k:>2} order={r.order:>2} m0={r.m0:>2} coeffs=({coeffs})", flush=True)
    if args.json_out:
        _write_json(args.json_out, payload)
        print(f"[pom-cli] wrote {args.json_out}", flush=True)


def _sqrt_phi() -> float:
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    return phi**0.5


def cmd_fold_spectrum(args: argparse.Namespace) -> None:
    # We intentionally reuse the "paper-canonical" Perron roots stored in the audited script.
    import exp_fold_collision_renyi_spectrum as rs

    q_max = int(args.q_max)
    if q_max < 2:
        raise SystemExit("Require q_max >= 2")

    r2 = rs.perron_root_r2()
    r3 = rs.perron_root_r3()
    r4 = rs.perron_root_r4()

    sqphi = _sqrt_phi()
    rows: List[Dict[str, Any]] = []
    for q in range(2, q_max + 1):
        if q == 2:
            rq = float(r2)
            note = "exact (A2)"
        elif q == 3:
            rq = float(r3)
            note = "exact (A3)"
        elif q == 4:
            rq = float(r4)
            note = "exact (A4)"
        elif q in rs.PRECOMPUTED_RQ:
            rq = float(rs.PRECOMPUTED_RQ[q])
            note = "exact (recurrence)"
        else:
            raise SystemExit(f"Missing r_q for q={q}. Use q<=17, or run the DP estimator scripts.")

        hq = q * math.log(2.0) - math.log(rq)
        rows.append(
            {
                "q": q,
                "r_q": rq,
                "h_q": hq,
                "r_q_pow_1_over_q": rq ** (1.0 / q),
                "sqrt_phi": sqphi,
                "gap_to_sqrt_phi": (rq ** (1.0 / q)) - sqphi,
                "note": note,
            }
        )

    # Print a compact, audit-friendly table.
    print("[pom-cli] Fold_m Renyi-q fingerprint (paper-canonical r_q)", flush=True)
    print("[pom-cli] columns: q  r_q  h_q=log(2^q/r_q)  r_q^(1/q)  gap_to_sqrt(phi)", flush=True)
    for r in rows:
        print(
            f"[pom-cli] q={r['q']:>2}  r_q={r['r_q']:.12f}  h_q={r['h_q']:.12f}  "
            f"r_q^(1/q)={r['r_q_pow_1_over_q']:.12f}  gap={r['gap_to_sqrt_phi']:.12f}  {r['note']}",
            flush=True,
        )

    if args.json_out:
        _write_json(args.json_out, {"q_max": q_max, "rows": rows})
        print(f"[pom-cli] wrote {args.json_out}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="POM CLI: normalize projection-words; summarize Fold_m fingerprints.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_norm = sub.add_parser("normalize", help="Normalize a projection word (rewrite to normal form).")
    p_norm.add_argument("--fragment", choices=["ze", "zepq", "liftproj", "val"], default="liftproj")
    p_norm.add_argument("--word", type=str, default=None, help="Optional raw word string (fragment-dependent).")
    p_norm.add_argument("--json-out", type=str, default=None, help="Write normalization payload to JSON.")
    p_norm.add_argument("tokens", nargs="*", help="Token list (used when --word is omitted).")
    p_norm.set_defaults(func=cmd_normalize)

    p_eq = sub.add_parser("equiv", help="Decide equivalence by comparing normal forms.")
    p_eq.add_argument("--fragment", choices=["ze", "zepq", "liftproj", "val"], default="liftproj")
    p_eq.add_argument("--word1", type=str, required=True, help="Word 1 (fragment-dependent string form).")
    p_eq.add_argument("--word2", type=str, required=True, help="Word 2 (fragment-dependent string form).")
    p_eq.set_defaults(func=cmd_equiv)

    p_recs = sub.add_parser("fold-recs", help="Print verified integer recurrences for S_k(m).")
    p_recs.add_argument("--k-max", type=int, default=17)
    p_recs.add_argument("--json-out", type=str, default=None)
    p_recs.set_defaults(func=cmd_fold_recs)

    p_spec = sub.add_parser("fold-spectrum", help="Print Renyi-q fingerprint spectrum (canonical r_q).")
    p_spec.add_argument("--q-max", type=int, default=17)
    p_spec.add_argument("--json-out", type=str, default=None)
    p_spec.set_defaults(func=cmd_fold_spectrum)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

