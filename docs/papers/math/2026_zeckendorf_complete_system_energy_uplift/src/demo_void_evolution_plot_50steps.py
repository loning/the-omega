#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a single large figure visualizing 50-step void evolution.

Outputs:
  - void_evolution_50steps.png

This script re-runs the same process as demo_void_evolution_50steps.py, but records
time series and per-branch details, then renders a high-resolution multi-panel plot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem
from zeckendorf_ontic.observer import Observer, Transition
from zeckendorf_ontic.protocol import ZeckendorfProtocol


@dataclass(frozen=True)
class StepSnapshot:
    step: int
    W: int
    space_cost_total: int
    branch_count: int
    y_obs: int
    unique_micro_count: int


@dataclass(frozen=True)
class BranchPoint:
    step: int
    micro_integer: int
    tail_word: int
    trace_len: int
    space_cost: int


def _bits_msb(x: int, width: int) -> str:
    return format(int(x), "0{}b".format(int(width)))


def _min_W0_for_n_steps(build, *, steps: int, max_W: int = 20000) -> int:
    for W in range(1, int(max_W) + 1):
        try:
            o = build(int(W))
        except ValueError:
            continue
        ok = True
        for _ in range(int(steps)):
            o.protocol_expand_one_step_and_commit()
            if not o.branch_count():
                ok = False
                break
            if o.space_cost_y6() > o.resource_limit:
                ok = False
                break
        if ok:
            return int(W)
    raise RuntimeError("failed to find a feasible W0 for the requested step count")


def _collect_one_step(
    *,
    step: int,
    observer: Observer,
    proto: ZeckendorfProtocol,
    window_length: int,
    tail_len: int,
) -> Tuple[StepSnapshot, List[BranchPoint], Set[int]]:
    if observer.branch_count() <= 0:
        raise RuntimeError("observer has no branches")

    # Collect current branches ordered exactly as commit uses (score_key).
    ordered = sorted(
        [b for b in observer._branches if proto.is_ok_clo(b.protocol_state())],
        key=lambda b: proto.score_key(b.protocol_state()),
    )

    micro_set: Set[int] = set()
    points: List[BranchPoint] = []
    for b in ordered:
        micro_integer = int(proto.score_key(b.protocol_state())[0])
        micro_set.add(int(micro_integer))
        points.append(
            BranchPoint(
                step=int(step),
                micro_integer=int(micro_integer),
                tail_word=int(b.tail_word),
                trace_len=int(b.trace_tape_length),
                space_cost=int(b.space_cost_y6()),
            )
        )

    snap = StepSnapshot(
        step=int(step),
        W=int(observer.resource_limit),
        space_cost_total=int(observer.space_cost_y6()),
        branch_count=int(observer.branch_count()),
        y_obs=int(observer.observed_macro_word(observation_setting=step)),
        unique_micro_count=int(len(micro_set)),
    )
    return snap, points, micro_set


def _render_plot(
    *,
    out_path: str,
    snaps: List[StepSnapshot],
    points: List[BranchPoint],
    micro_timeline: List[Set[int]],
    window_length: int,
    tail_len: int,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "matplotlib is required for plotting. Install it (e.g. pip install matplotlib)."
        ) from e

    steps = [s.step for s in snaps]
    W = [s.W for s in snaps]
    cost = [s.space_cost_total for s in snaps]
    branches = [s.branch_count for s in snaps]
    uniq = [s.unique_micro_count for s in snaps]
    y_obs_bits = [_bits_msb(s.y_obs, window_length) for s in snaps]

    # Determine a stable micro ordering for the heatmap.
    all_micros: List[int] = sorted({m for ms in micro_timeline for m in ms})
    micro_to_row = {m: i for i, m in enumerate(all_micros)}

    # Build presence matrix: rows = micro integers, cols = steps.
    import numpy as np

    pres = np.zeros((max(1, len(all_micros)), max(1, len(steps))), dtype=int)
    for j, ms in enumerate(micro_timeline):
        for m in ms:
            pres[micro_to_row[m], j] = 1

    # Figure.
    fig = plt.figure(figsize=(22, 14), dpi=200, constrained_layout=True)
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 1.2], hspace=0.25, wspace=0.15)

    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])
    ax4 = fig.add_subplot(gs[2, :])

    ax0.plot(steps, W, linewidth=2.0)
    ax0.set_title("Resource cap W (endogenous gain)")
    ax0.set_xlabel("step")
    ax0.set_ylabel("W")
    ax0.grid(True, alpha=0.25)

    ax1.plot(steps, cost, linewidth=2.0, color="tab:orange", label="total space_cost")
    ax1.plot(steps, branches, linewidth=2.0, color="tab:green", label="branch_count")
    ax1.plot(steps, uniq, linewidth=2.0, color="tab:purple", label="unique micro count")
    ax1.set_title("Bubble size: total cost vs branches vs discovered micro explanations")
    ax1.set_xlabel("step")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="upper left", frameon=False)

    # Per-branch scatter: space_cost and trace_len vs step.
    ax2.set_title("Per-branch space_cost over time (each dot is a kept branch)")
    ax2.set_xlabel("step")
    ax2.set_ylabel("space_cost (Y6 blocks)")
    for p in points:
        ax2.scatter(p.step, p.space_cost, s=14, alpha=0.6)
    ax2.grid(True, alpha=0.25)

    ax3.set_title("Per-branch tail_word vs step (colored by micro_integer)")
    ax3.set_xlabel("step")
    ax3.set_ylabel("tail_word (integer)")
    if points:
        micros_sorted = sorted({p.micro_integer for p in points})
        color_map = {m: i for i, m in enumerate(micros_sorted)}
        for p in points:
            ax3.scatter(p.step, p.tail_word, s=14, alpha=0.7, c=[color_map[p.micro_integer]])
        ax3.set_yticks(list(range(0, 1 << int(tail_len))))
    ax3.grid(True, alpha=0.25)

    # Heatmap: presence of micro explanations over steps.
    ax4.set_title("Which micro explanations are present in the bubble (heatmap)")
    ax4.set_xlabel("step")
    ax4.set_ylabel("micro_integer (sorted)")
    im = ax4.imshow(pres, aspect="auto", interpolation="nearest")
    ax4.set_yticks(list(range(len(all_micros))))
    ax4.set_yticklabels([str(m) for m in all_micros])
    ax4.set_xticks(steps[::5] if len(steps) > 0 else [])
    ax4.set_xticklabels([str(s) for s in steps[::5]])

    # Annotate a few y_obs values at the very top for quick visual correlation.
    if steps:
        for j in range(0, len(steps), 5):
            ax4.text(j, -0.8, y_obs_bits[j], fontsize=8, rotation=45, ha="left", va="bottom")

    fig.suptitle("Void evolution (m=6, y_con=0^6): 50-step bubble growth + endogenous W", fontsize=16)
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    window_length = 6
    macro_word = 0  # y_con = 0^6
    steps_total = 50

    ontic = OnticZeckendorfSystem(window_length=window_length)
    proto = ZeckendorfProtocol(ontic)
    tail_len = int(ontic.tail_length())

    transition_table: Dict[Tuple[str, str], Transition] = {
        ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        ("START", "0"): Transition(next_state="START", write_symbol="0", head_move=0),
        ("START", "1"): Transition(next_state="START", write_symbol="1", head_move=0),
    }

    def build(W0: int) -> Observer:
        return Observer(
            proto,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=macro_word,
            tail_word_start=0,
            resource_limit=int(W0),
            tape_input_bits=None,
            couple_protocol_each_step=False,
        )

    W0 = _min_W0_for_n_steps(build, steps=steps_total)
    observer = build(W0)

    snaps: List[StepSnapshot] = []
    points: List[BranchPoint] = []
    micro_timeline: List[Set[int]] = []

    print("=== Plotting void evolution ===")
    print(f"m=6, y_con={_bits_msb(macro_word, window_length)}, steps={steps_total}, W0={W0}")

    for step in range(0, steps_total):
        observer.protocol_expand_one_step_and_commit()
        snap, pts, micro_set = _collect_one_step(
            step=step,
            observer=observer,
            proto=proto,
            window_length=window_length,
            tail_len=tail_len,
        )
        snaps.append(snap)
        points.extend(pts)
        micro_timeline.append(micro_set)

    out_path = "void_evolution_50steps.png"
    _render_plot(
        out_path=out_path,
        snaps=snaps,
        points=points,
        micro_timeline=micro_timeline,
        window_length=window_length,
        tail_len=tail_len,
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

