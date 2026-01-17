# -*- coding: utf-8 -*-
"""
Figure + GIF: dynamic "flipbook" geometry under the tick-first readout dictionary.

Goal
----
Generate an intuitive, movie-like visualization of "passing through layers of pages"
while staying faithful to the paper's protocol objects:
  - tick (scan iteration count)
  - window words Omega_m and stable types X_m
  - Fold_m(k) (Zeckendorf truncation) via exp_foldm_stats.cached_foldm_outputs
  - Hilbert addressing as a locality-preserving screen basis (2D Hilbert curve)
  - wormhole-like pointer jumps as paid shortcut updates (protocol-level)
  - an explicit cost ledger (E_wh) and an on/off counterfactual baseline

Outputs
-------
  - figures/dynamic_flipbook/dynamic_flipbook_overview.png
  - figures/dynamic_flipbook/dynamic_flipbook_wormhole_on.gif
  - figures/dynamic_flipbook/dynamic_flipbook_wormhole_off.gif
  - figures/dynamic_flipbook/dynamic_flipbook_ledger.png
  - sections/generated/dynamic_flipbook_summary.tex

Notes
-----
  - Deterministic: no randomness, no timestamps.
  - English-only text in plots (repo convention).
  - Uses a small scientific stack already used by other figure scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import ConnectionPatch, Rectangle  # noqa: E402

from PIL import Image  # noqa: E402

from common_paths import figures_dir, generated_dir  # noqa: E402
from common_progress import ProgressEvery  # noqa: E402
import exp_foldm_stats as foldm  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402


def _popcount01(s: str) -> int:
    return int(s.count("1"))


@dataclass(frozen=True)
class Layer:
    m: int
    n_bits: int
    L: int
    name: str
    img: np.ndarray  # (L,L) float in [0,1]
    k_map: np.ndarray  # (L,L) int, Hilbert index at each pixel


def _build_layer(m: int) -> Layer:
    if m < 1:
        raise ValueError("m must be >= 1")
    if (m % 2) != 0:
        raise ValueError("This visualization uses the balanced 2D Hilbert screen: require even m (so 2^m = 4^n).")
    n_bits = m // 2
    L = 1 << n_bits
    N = 1 << m

    outs = foldm.cached_foldm_outputs(m)
    if len(outs) != N:
        raise AssertionError("Fold_m output length mismatch.")

    path = hil.hilbert_curve(n_bits)  # list[(x,y)] length 4^n_bits = 2^m
    if len(path) != N:
        raise AssertionError("Hilbert path length mismatch.")

    img = np.zeros((L, L), dtype=float)
    k_map = np.zeros((L, L), dtype=int)

    denom_suffix = max(1, m - 6)
    for k, (x, y) in enumerate(path):
        w = outs[k]
        # Paper-facing split used in other figures:
        #   prefix u = first 6 bits (anchor interface),
        #   suffix = uplift microtexture.
        if m <= 6:
            val = _popcount01(w) / float(m) if m > 0 else 0.0
        else:
            suffix = w[6:]
            val = _popcount01(suffix) / float(denom_suffix)
        img[int(y), int(x)] = float(val)
        k_map[int(y), int(x)] = int(k)

    name = f"m={m} (screen {L}×{L})"
    return Layer(m=m, n_bits=n_bits, L=L, name=name, img=img, k_map=k_map)


def _horizon_mask(layer: Layer, q: float = 0.88) -> np.ndarray:
    """
    Deterministic "budget horizon" proxy mask: top-quantile of the uplift field.
    This is a visualization-only proxy (not a theorem-level object).
    """
    flat = layer.img.reshape(-1)
    thr = float(np.quantile(flat, q))
    return (layer.img >= thr)


def _render_overview(layers: List[Layer], out_png: Path) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12.6, 6.4))

    # Layout: three panels with slight overlap to suggest depth.
    positions = [
        (0.06, 0.15, 0.28, 0.72),
        (0.36, 0.18, 0.30, 0.68),
        (0.68, 0.21, 0.28, 0.64),
    ]
    axes = []
    for layer, (x0, y0, w, h) in zip(layers, positions):
        ax = fig.add_axes([x0, y0, w, h])
        axes.append(ax)
        ax.imshow(layer.img, cmap="turbo", origin="lower", interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(layer.name, fontsize=12, pad=6)
        # Outline frame
        ax.add_patch(Rectangle((-0.5, -0.5), layer.L, layer.L, fill=False, lw=1.5, ec="#263238"))

    # A simple arrow of "through layers" direction.
    fig.text(0.50, 0.06, "tick-first scan: pass through layers (resolution uplift)", ha="center", fontsize=12)
    fig.text(0.50, 0.025, "color = uplift microtexture density (suffix bits of Fold_m)", ha="center", fontsize=10, color="#455A64")

    # Connector arrows between panels.
    for a, b in zip(axes[:-1], axes[1:]):
        con = ConnectionPatch(
            xyA=(1.02, 0.5),
            coordsA=a.transAxes,
            xyB=(-0.02, 0.5),
            coordsB=b.transAxes,
            arrowstyle="-|>",
            mutation_scale=16,
            lw=2.0,
            color="#546E7A",
        )
        fig.add_artist(con)

    fig.suptitle("Dynamic flipbook geometry (protocol-facing): pages are Hilbert screens at increasing m", fontsize=14, y=0.98)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


@dataclass
class RunSpec:
    wormhole_on: bool
    gif_name: str
    jump_frame: int
    jump_target_frac: float
    jump_cost: float


def _compose_frame(
    layers: List[Layer],
    stage: int,
    stage_frac: float,
    visited: List[np.ndarray],
    cursor_xy: List[Tuple[int, int]],
    horizon: Optional[np.ndarray],
    jump_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]],
    ledger_Ewh: float,
    t_global: int,
) -> Image.Image:
    """
    Compose one frame as a static PNG-like raster (returned as PIL Image).
    """
    fig = plt.figure(figsize=(10.4, 6.4))

    # Page stack layout (depth illusion by size/position).
    pos = [
        (0.06, 0.14, 0.28, 0.74),
        (0.36, 0.18, 0.30, 0.70),
        (0.70, 0.22, 0.26, 0.62),
    ]
    axes: List[plt.Axes] = []

    for li, (layer, (x0, y0, w, h)) in enumerate(zip(layers, pos)):
        ax = fig.add_axes([x0, y0, w, h])
        axes.append(ax)

        mask = visited[li]
        img = np.where(mask, layer.img, 0.0)
        ax.imshow(img, cmap="turbo", origin="lower", interpolation="nearest", vmin=0.0, vmax=1.0)

        # Active layer highlight.
        active = (li == stage)
        frame_color = "#FF6F00" if active else "#263238"
        frame_lw = 2.5 if active else 1.2
        ax.add_patch(Rectangle((-0.5, -0.5), layer.L, layer.L, fill=False, lw=frame_lw, ec=frame_color))

        # Horizon outline on active layer only.
        if active and horizon is not None:
            ax.contour(horizon.astype(float), levels=[0.5], colors=["#FFFFFF"], linewidths=1.2, alpha=0.95, origin="lower")

        # Cursor marker (scan head).
        cx, cy = cursor_xy[li]
        ax.scatter([cx], [cy], s=80 if active else 40, c=frame_color, edgecolors="white", linewidths=0.7, zorder=6)

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(layer.name, fontsize=11, pad=4)

    # Jump line (draw on active axes).
    if jump_line is not None:
        (x1, y1), (x2, y2) = jump_line
        ax = axes[stage]
        ax.plot([x1, x2], [y1, y2], color="#00E5FF", lw=2.6, alpha=0.95, zorder=7)
        ax.scatter([x1, x2], [y1, y2], s=46, c="#00E5FF", edgecolors="black", linewidths=0.6, zorder=8)
        ax.text(
            0.02,
            0.02,
            "pointer jump (paid shortcut)",
            transform=ax.transAxes,
            fontsize=9,
            color="#00E5FF",
            ha="left",
            va="bottom",
            bbox=dict(facecolor=(0, 0, 0, 0.45), edgecolor="none", pad=3),
        )

    # Global HUD: tick and ledger.
    fig.text(0.02, 0.95, f"tick t = {t_global:04d}", fontsize=12, ha="left", va="top", color="#263238")
    fig.text(0.98, 0.95, f"E_wh ledger = {ledger_Ewh:.3f}", fontsize=12, ha="right", va="top", color="#263238")
    fig.text(0.50, 0.06, "scan reveals pixels in Hilbert order; active page changes with resolution uplift", ha="center", fontsize=11)
    fig.text(0.50, 0.03, "unrevealed pixels are black; white contour is a deterministic 'budget-horizon' proxy", ha="center", fontsize=9, color="#455A64")

    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((h, w, 4))
    # ARGB -> RGBA
    rgba = buf[:, :, [1, 2, 3, 0]]
    im = Image.fromarray(rgba, mode="RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
    plt.close(fig)
    return im


def _build_xy_index(layer: Layer) -> Dict[int, Tuple[int, int]]:
    """
    Return map: Hilbert index k -> (x,y) coordinate on the screen.
    """
    path = hil.hilbert_curve(layer.n_bits)
    out: Dict[int, Tuple[int, int]] = {}
    for k, (x, y) in enumerate(path):
        out[int(k)] = (int(x), int(y))
    return out


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _save_frame_png(im: Image.Image, out_png: Path) -> None:
    # Keep PNGs small-ish and deterministic.
    im.convert("RGBA").save(out_png, format="PNG", optimize=False)


def _render_contact_sheet(
    gif_path: Path,
    out_png: Path,
    rows: int = 4,
    cols: int = 6,
    margin: int = 10,
    title: str = "",
) -> None:
    """
    Render a contact sheet from an existing GIF by sampling frames uniformly.
    This is robust when a viewer does not autoplay GIFs (e.g. some IDE previews).
    """
    im = Image.open(gif_path)
    n = int(getattr(im, "n_frames", 1))
    if n <= 1:
        raise ValueError("GIF has <=1 frame; contact sheet would be pointless.")

    k = rows * cols
    idxs = [int(round(i * (n - 1) / float(max(1, k - 1)))) for i in range(k)]
    frames: List[Image.Image] = []
    for j in idxs:
        im.seek(j)
        frames.append(im.convert("RGB"))

    w, h = frames[0].size
    head_h = 38 if title else 0
    W = cols * w + (cols + 1) * margin
    H = rows * h + (rows + 1) * margin + head_h
    canvas = Image.new("RGB", (W, H), color=(255, 255, 255))

    if title:
        # Simple title band (avoid font deps; draw via matplotlib for consistent text).
        fig = plt.figure(figsize=(W / 140.0, head_h / 140.0))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis("off")
        ax.text(0.5, 0.5, title, ha="center", va="center", fontsize=14, color="#263238")
        fig.canvas.draw()
        ww, hh = fig.canvas.get_width_height()
        buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
        rgba = buf[:, :, [1, 2, 3, 0]]
        title_img = Image.fromarray(rgba, mode="RGBA").convert("RGB")
        plt.close(fig)
        canvas.paste(title_img, (0, 0))

    y0 = head_h
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            x = margin + c * (w + margin)
            y = y0 + margin + r * (h + margin)
            canvas.paste(frames[idx], (x, y))

    _ensure_dir(out_png.parent)
    canvas.save(out_png, format="PNG", optimize=False)


def _simulate_and_render_gif(
    layers: List[Layer],
    spec: RunSpec,
    out_gif: Path,
    fps: int = 15,
    out_frames_dir: Optional[Path] = None,
) -> Tuple[List[float], List[float]]:
    """
    Render a deterministic GIF and return time series:
      - t_list (float)
      - Ewh_list (float)
    """
    out_gif.parent.mkdir(parents=True, exist_ok=True)

    frames = 240  # 16s at 15 fps (more time to "feel" the movie)
    stage_len = frames // len(layers)
    if stage_len <= 0:
        raise AssertionError("Invalid stage length.")

    # Per-layer scan state: visited mask and cursor index (Hilbert index).
    visited = [np.zeros((ly.L, ly.L), dtype=bool) for ly in layers]
    cursor_k = [0 for _ in layers]
    xy_of_k = [_build_xy_index(ly) for ly in layers]

    # Deterministic horizon proxy computed on the middle layer (m=10) for visibility.
    horizon = _horizon_mask(layers[1], q=0.88) if len(layers) >= 2 else None

    ledger_Ewh = 0.0
    Ewh_list: List[float] = []
    t_list: List[float] = []

    pe = ProgressEvery(label=f"render_gif({spec.gif_name})", total=frames, interval_s=60.0)
    pe.start()

    gif_frames: List[Image.Image] = []
    if out_frames_dir is not None:
        _ensure_dir(out_frames_dir)
    last_jump_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
    last_jump_t = -10**9

    for f in range(frames):
        pe.maybe(f)

        stage = min(len(layers) - 1, f // stage_len)
        stage_f0 = stage * stage_len
        stage_frac = (f - stage_f0) / float(max(1, stage_len - 1))

        # Scan speed: reveal a bounded amount per frame, scaling with screen size.
        ly = layers[stage]
        N = 1 << ly.m
        # Aim: reveal ~90% of the page during its stage (more visible motion).
        visits_per_frame = max(1, int((0.90 * N) / float(stage_len)))

        # Wormhole event (only applied in the middle stage for readability).
        if spec.wormhole_on and (f == spec.jump_frame):
            if stage != 1 and len(layers) >= 2:
                # If jump_frame does not land in stage 1 due to configuration changes,
                # keep the event but do it on the current stage.
                pass
            prev_k = int(cursor_k[stage])
            target = int(max(0, min(N - 1, int(spec.jump_target_frac * float(N)))))
            cursor_k[stage] = target
            ledger_Ewh += float(spec.jump_cost)
            last_jump_line = (xy_of_k[stage][prev_k], xy_of_k[stage][target])
            last_jump_t = int(f)

        # Reveal new visited indices (non-prefix model: visited set, not a prefix).
        for _ in range(visits_per_frame):
            k = int(cursor_k[stage])
            x, y = xy_of_k[stage][k]
            visited[stage][y, x] = True
            cursor_k[stage] = (k + 1) % N

        # Cursor locations for HUD markers.
        cursor_xy = []
        for li, l in enumerate(layers):
            kk = int(cursor_k[li])
            cursor_xy.append(xy_of_k[li][kk])

        # Keep jump line visible for a short time window.
        jump_line = last_jump_line if (f - last_jump_t) <= int(0.7 * fps) else None

        # Horizon shown only when the active stage is the middle layer.
        horizon_now = horizon if (stage == 1) else None

        im = _compose_frame(
            layers=layers,
            stage=stage,
            stage_frac=stage_frac,
            visited=visited,
            cursor_xy=cursor_xy,
            horizon=horizon_now,
            jump_line=jump_line,
            ledger_Ewh=ledger_Ewh,
            t_global=f,
        )
        gif_frames.append(im)
        if out_frames_dir is not None:
            _save_frame_png(im, out_frames_dir / f"frame_{f:04d}.png")
        t_list.append(float(f) / float(fps))
        Ewh_list.append(float(ledger_Ewh))

    # Save GIF (loop=0: infinite loop).
    gif_frames[0].save(
        out_gif,
        save_all=True,
        append_images=gif_frames[1:],
        duration=int(1000 / fps),
        loop=0,
        optimize=False,
        disposal=2,
    )
    pe.done(extra=f"wrote={out_gif}")
    return t_list, Ewh_list


def _render_ledger(t: List[float], e_on: List[float], e_off: List[float], out_png: Path) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9.8, 3.8))
    ax.plot(t, e_off, lw=2.2, color="#455A64", label="wormhole off (E_wh=0)")
    ax.plot(t, e_on, lw=2.2, color="#1E88E5", label="wormhole on (paid jumps)")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("E_wh ledger (arb. units)")
    ax.grid(True, color="#ECEFF1")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Paid pointer-jump ledger (protocol-facing): counterfactual baseline vs wormhole-on", pad=10)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_tex_summary(paths: List[Path]) -> None:
    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    rel = [p.as_posix() for p in paths]
    lines = [
        r"\paragraph{Dynamic flipbook visualization (figures/gif).} \AuditTag "
        + r"We provide a deterministic, protocol-facing animation of tick-first scan readout on Hilbert screens at increasing resolution $m$, "
        + r"including a paid pointer-jump shortcut (wormhole-like channel) and an explicit wormhole-on/off counterfactual baseline. ",
        r"\AuditTag Artifacts:",
        r"\begin{itemize}",
    ]
    for p in rel:
        lines.append(rf"\item \texttt{{{p}}}")
    lines += [r"\end{itemize}"]
    (out_dir / "dynamic_flipbook_summary.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    # Layers: anchor -> uplift -> deeper uplift.
    layers = [_build_layer(6), _build_layer(10), _build_layer(14)]

    fig_dir = figures_dir() / "dynamic_flipbook"
    fig_dir.mkdir(parents=True, exist_ok=True)

    out_overview = fig_dir / "dynamic_flipbook_overview.png"
    _render_overview(layers=layers, out_png=out_overview)
    print(f"Wrote {out_overview}")

    # GIF specs (place the jump near the middle of the middle stage).
    fps = 15
    frames = 240
    stage_len = frames // len(layers)
    jump_frame = stage_len + (stage_len // 2)  # middle of stage-2 (m=10)

    spec_on = RunSpec(
        wormhole_on=True,
        gif_name="wormhole_on",
        jump_frame=int(jump_frame),
        jump_target_frac=0.78,
        jump_cost=0.150,
    )
    spec_off = RunSpec(
        wormhole_on=False,
        gif_name="wormhole_off",
        jump_frame=int(jump_frame),
        jump_target_frac=0.78,
        jump_cost=0.150,
    )

    out_gif_on = fig_dir / "dynamic_flipbook_wormhole_on.gif"
    out_gif_off = fig_dir / "dynamic_flipbook_wormhole_off.gif"

    frames_on_dir = fig_dir / "frames_wormhole_on"
    frames_off_dir = fig_dir / "frames_wormhole_off"
    t_on, e_on = _simulate_and_render_gif(layers=layers, spec=spec_on, out_gif=out_gif_on, fps=fps, out_frames_dir=frames_on_dir)
    t_off, e_off = _simulate_and_render_gif(layers=layers, spec=spec_off, out_gif=out_gif_off, fps=fps, out_frames_dir=frames_off_dir)
    print(f"Wrote {out_gif_on}")
    print(f"Wrote {out_gif_off}")

    out_ledger = fig_dir / "dynamic_flipbook_ledger.png"
    _render_ledger(t=t_on, e_on=e_on, e_off=e_off, out_png=out_ledger)
    print(f"Wrote {out_ledger}")

    # Contact sheets (for environments that do not autoplay GIFs).
    out_cs_on = fig_dir / "dynamic_flipbook_wormhole_on_contact_sheet.png"
    out_cs_off = fig_dir / "dynamic_flipbook_wormhole_off_contact_sheet.png"
    _render_contact_sheet(
        gif_path=out_gif_on,
        out_png=out_cs_on,
        rows=4,
        cols=6,
        title="wormhole on (sampled frames): flipbook scan + paid pointer jump",
    )
    _render_contact_sheet(
        gif_path=out_gif_off,
        out_png=out_cs_off,
        rows=4,
        cols=6,
        title="wormhole off (sampled frames): flipbook scan baseline",
    )
    print(f"Wrote {out_cs_on}")
    print(f"Wrote {out_cs_off}")

    _write_tex_summary(
        paths=[
            out_overview,
            out_gif_on,
            out_gif_off,
            out_cs_on,
            out_cs_off,
            out_ledger,
            frames_on_dir,
            frames_off_dir,
        ]
    )
    print("Wrote sections/generated/dynamic_flipbook_summary.tex")


if __name__ == "__main__":
    main()

