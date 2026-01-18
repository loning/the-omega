# -*- coding: utf-8 -*-
"""
ISA-VIZ1: Centerwired decoder demo (Z128-style m=6 -> m=8/10 refinement).

This script wires the existing centerwired decoder figure into the paper as a
generated LaTeX fragment, and optionally regenerates the figure assets from a
local GenBank record.

Outputs:
  - sections/generated/centerwired_decoder_demo.tex (+ meta)

Repro (regenerate figures; overwrites files under figures/):
  python scripts/exp_centerwired_decoder_demo.py --render --force

Notes
-----
The visualization treats the three m=6 boundary words {100001,100101,101001} as
"control symbols" that gate a local refinement schedule on an 8x8 Hilbert
screen. This is an explanatory interface convention, not an empirical claim.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic


SCRIPT_VERSION = 3


def root_dir() -> Path:
    return SCRIPT_DIR.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint_file(path: Path) -> dict[str, object]:
    st = path.stat()
    return {"name": path.name, "bytes": int(st.st_size), "sha256": _sha256_file(path)}


def _extract_genbank_origin_seq(gb_path: Path) -> str:
    text = gb_path.read_text(encoding="utf-8", errors="replace")
    if "ORIGIN" not in text:
        raise SystemExit(f"GenBank record missing ORIGIN: {gb_path}")
    origin = text.split("ORIGIN", 1)[1]
    origin = origin.split("//", 1)[0]
    seq_parts: list[str] = []
    for raw in origin.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line[0].isdigit():
            # Typical ORIGIN lines: "<idx> <bases...>"
            parts = line.split()
            if len(parts) >= 2:
                seq_parts.append("".join(parts[1:]))
        else:
            seq_parts.append(re.sub(r"[^A-Za-z]", "", line))
    seq = "".join(seq_parts).upper().replace("U", "T")
    seq = re.sub(r"[^ACGTN]", "", seq)
    if not seq:
        raise SystemExit(f"Failed to extract sequence from GenBank ORIGIN: {gb_path}")
    return seq


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ISA-VIZ1: wire centerwired decoder demo figure into the paper.")
    ap.add_argument(
        "--genbank",
        default=str(root_dir() / "data" / "recoding_genbank" / "genbank" / "AB019694.1.gb"),
        help="Local GenBank flatfile used for the demo (default: AB019694.1.gb).",
    )
    ap.add_argument("--name", default="AB019694", help="Label shown on the rendered frames.")
    ap.add_argument("--frames", type=int, default=6, help="Number of frames to render (for --render).")
    ap.add_argument("--stride", type=int, default=240, help="Stride (bases) between frames (for --render).")
    ap.add_argument("--start", type=int, default=0, help="Start offset in bases (for --render).")
    ap.add_argument("--scale", type=int, default=6, help="Cell scale (for --render; maps to coarse cell pixel size).")
    ap.add_argument("--delta-m10", default="55", help="Comma-separated Δ values that trigger m=10 (for --render).")
    ap.add_argument(
        "--out-prefix",
        default=str(root_dir() / "figures" / "ab019694_centerwired_gates"),
        help="Output prefix (no extension) for rendered figures (for --render).",
    )
    ap.add_argument("--render", action="store_true", help="Regenerate figure assets under figures/.")
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return ap.parse_args()


def _render_centerwired_assets(
    *,
    gb_path: Path,
    out_prefix: Path,
    name: str,
    frames: int,
    stride: int,
    start: int,
    scale: int,
    delta_m10: str,
) -> None:
    seq = _extract_genbank_origin_seq(gb_path)
    fig_script = SCRIPT_DIR / "fig_dna_hilbert_decoder_movie.py"
    if not fig_script.exists():
        raise SystemExit(f"Missing renderer script: {fig_script}")
    cmd = [
        sys.executable,
        str(fig_script),
        "--scheme",
        "centerwired",
        "--mode",
        "base",
        "--seq",
        seq,
        "--name",
        str(name),
        "--frames",
        str(int(frames)),
        "--stride",
        str(int(stride)),
        "--start",
        str(int(start)),
        "--scale",
        str(int(scale)),
        "--delta-m10",
        str(delta_m10),
        "--out-prefix",
        str(out_prefix),
    ]
    subprocess.run(cmd, cwd=str(root_dir()), check=True)


def main() -> None:
    args = parse_args()

    gb_path = Path(str(args.genbank))
    if not gb_path.is_absolute():
        gb_path = root_dir() / gb_path
    if not gb_path.exists():
        raise SystemExit(f"Missing GenBank record: {gb_path}")

    out_prefix = Path(str(args.out_prefix))
    if not out_prefix.is_absolute():
        out_prefix = root_dir() / out_prefix

    try:
        out_prefix_rel = str(out_prefix.relative_to(root_dir()))
    except Exception:
        out_prefix_rel = str(out_prefix)

    out_tex = generated_dir() / "centerwired_decoder_demo.tex"

    cache_key: dict[str, Any] = {
        "analysis": "centerwired_decoder_demo",
        "script_version": int(SCRIPT_VERSION),
        "gb": _fingerprint_file(gb_path),
        "params": {
            "name": str(args.name),
            "frames": int(args.frames),
            "stride": int(args.stride),
            "start": int(args.start),
            "scale": int(args.scale),
            "delta_m10": str(args.delta_m10),
            "out_prefix": out_prefix_rel,
        },
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        return

    if args.render:
        _render_centerwired_assets(
            gb_path=gb_path,
            out_prefix=out_prefix,
            name=str(args.name),
            frames=int(args.frames),
            stride=int(args.stride),
            start=int(args.start),
            scale=int(args.scale),
            delta_m10=str(args.delta_m10),
        )

    try:
        rel_prefix = out_prefix.relative_to(root_dir()) if out_prefix.is_absolute() else out_prefix
    except Exception:
        rel_prefix = out_prefix
    rel_contact = Path(str(rel_prefix) + "_contact_sheet.png")
    rel_legend = Path(str(rel_prefix) + "_legend.png")

    lines: list[str] = []
    lines.append(r"\paragraph{ISA-VIZ1: An executable multi-resolution (Z128) interface demo.}")
    lines.append(
        r"We include a concrete ``centerwired'' Hilbert decoder (adapted from the Z128 stable-sector framework) that "
        r"compiles each codon under $\mu^\ast$ to $(N,w,V,\Delta)$ and treats the three $m=6$ boundary words as a "
        r"minimal control alphabet gating local refinement to $m\in\{8,10\}$."
    )
    lines.append(r"\begin{figure}[H]")
    lines.append(r"\centering")
    lines.append(rf"\includegraphics[width=0.98\linewidth]{{{rel_contact.as_posix()}}}")
    lines.append(r"\caption{Centerwired decoder demonstration on \texttt{AB019694.1} (Sec example).")
    lines.append(
        r"Each coarse cell consumes a 3-mer prefix ($m=6$), colored by its Fold$_6$ stable type; "
        r"the three boundary words $\{\texttt{100001},\texttt{100101},\texttt{101001}\}$ are treated as control records "
        r"(thick border) that gate a local refinement schedule. "
        r"Inside refined mode, payload cells display microstructure as embedded Hilbert strokes ($m=8$: 1-base suffix; "
        r"$m=10$: 2-base suffix for selected $\Delta$ values). "
        r"This is a visualization convention illustrating how an $m=6$ Hilbert screen can carry local $m=8/m=10$ information; "
        r"it is not used as evidence for the biological endpoints.}"
    )
    lines.append(r"\label{fig:centerwired_decoder_demo}")
    lines.append(r"\end{figure}")
    lines.append(rf"\noindent\textbf{{Legend:}} \path{{{rel_legend.as_posix()}}}.")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines))
    write_json_atomic(cache_meta_path(out_tex), cache_meta)


if __name__ == "__main__":
    main()
