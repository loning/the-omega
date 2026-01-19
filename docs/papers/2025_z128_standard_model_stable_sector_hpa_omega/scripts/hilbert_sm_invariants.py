# -*- coding: utf-8 -*-
"""
Compute discrete invariants on CenterGraph objects.

This module focuses on auditable, deterministic invariants aligned with the paper:
  - chi_2d: discrete Hilbert chirality index (I_10, Eq. (hilbert_chi_def))
  - chi_3d: 3D oriented-volume turn sign sum (discrete chirality proxy)
  - spin_half_proxy: a minimal double-cover proxy from loop holonomy signs
  - anomaly checks: reuse integer arithmetic from exp_sm_labeling_solver
  - SU(3) holonomy proxy: reuse S4->SO(3) rotation-angle summary (exp_holonomy_su3_representation)
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Tuple

from hilbert_sm_center_graph import CenterGraph, iter_scan_points

import exp_hilbert_chirality_index as hilchi
import exp_sm_labeling_solver as sm
import exp_holonomy_loops as holo
import exp_holonomy_su3_representation as su3rep


def _sign(x: float, eps: float = 1e-12) -> int:
    if abs(x) <= eps:
        return 0
    return 1 if x > 0 else -1


def chi_2d_from_scan(g: CenterGraph) -> int:
    """
    Discrete chirality index on the scan polyline, using its (x,y) projection.
    Matches exp_hilbert_chirality_index.chirality_index when the path is the base Hilbert path.
    """
    pts = [(float(p[0]), float(p[1])) for p in iter_scan_points(g)]
    if len(pts) < 3:
        return 0
    total = 0
    for i in range(1, len(pts) - 1):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        total += _sign(cross)
    return int(total)

def local_turn_signs_2dproj(g: CenterGraph) -> Dict[int, int]:
    """
    Return local turn sign at each interior node along the scan path, using (x,y) projection.
    Node ids at endpoints are omitted.
    """
    ids = [int(v) for v in g.scan_path]
    pts = [(float(g.nodes[i].pt[0]), float(g.nodes[i].pt[1])) for i in ids]
    out: Dict[int, int] = {}
    for i in range(1, len(ids) - 1):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        out[ids[i]] = _sign(cross)
    return out


def _field_chirality_class(label_tex: str) -> str:
    """
    Map a SM label to a coarse chirality class for scoring.
    """
    s = str(label_tex)
    if "U(1)" in s or "SU(2)" in s or "SU(3)" in s:
        return "gauge"
    if "_L" in s:
        return "L"
    if "_R" in s or "\\nu_R" in s:
        return "R"
    return "other"


@dataclass(frozen=True)
class PhysicsScore:
    score: float
    details: Dict[str, float]


def score_physics_chirality_alignment(g: CenterGraph) -> PhysicsScore:
    """
    Experimental scoring objective:
      - Prefer L-labeled nodes to sit on negative turns (sign=-1)
      - Prefer R-labeled nodes to sit on positive turns (sign=+1)
      - Penalize opposite alignment
      - Small bonus for large |chi| and for negative global chi (weak-parity choice)
    """
    turns = local_turn_signs_2dproj(g)
    nL = nR = nG = 0
    L_good = L_bad = R_good = R_bad = 0
    zeros = 0
    for nid, sgn in turns.items():
        cls = _field_chirality_class(g.nodes[int(nid)].label_tex)
        if sgn == 0:
            zeros += 1
            continue
        if cls == "L":
            nL += 1
            if sgn < 0:
                L_good += 1
            else:
                L_bad += 1
        elif cls == "R":
            nR += 1
            if sgn > 0:
                R_good += 1
            else:
                R_bad += 1
        elif cls == "gauge":
            nG += 1

    chi = float(chi_2d_from_scan(g))
    align = float(L_good + R_good) - 1.5 * float(L_bad + R_bad)
    chi_mag_bonus = 0.01 * abs(chi)
    chi_sign_bonus = 0.2 if chi < 0 else 0.0
    score = align + chi_mag_bonus + chi_sign_bonus

    details = {
        "align": align,
        "chi": chi,
        "chi_mag_bonus": chi_mag_bonus,
        "chi_sign_bonus": chi_sign_bonus,
        "L_good": float(L_good),
        "L_bad": float(L_bad),
        "R_good": float(R_good),
        "R_bad": float(R_bad),
        "turn_zeros": float(zeros),
        "nL_scored": float(nL),
        "nR_scored": float(nR),
        "nG_seen": float(nG),
    }
    return PhysicsScore(score=float(score), details=details)


def chi_3d_from_scan(g: CenterGraph) -> int:
    """
    3D chirality proxy from oriented triple products of consecutive direction vectors.
    For each triple of points p_{i-1}, p_i, p_{i+1}, compute v1 = p_i-p_{i-1}, v2 = p_{i+1}-p_i.
    Then use the sign of (v1 x v2)·e_ref, where e_ref is chosen as the next nonzero direction when available.

    This is a conservative discrete proxy; it becomes more meaningful in genuinely 3D scan segments.
    """
    pts = [tuple(float(x) for x in p) for p in iter_scan_points(g)]
    if len(pts) < 4:
        return 0
    total = 0
    for i in range(1, len(pts) - 2):
        p0 = pts[i - 1]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]) if g.dim == 3 else (p1[0] - p0[0], p1[1] - p0[1], 0.0)
        v2 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]) if g.dim == 3 else (p2[0] - p1[0], p2[1] - p1[1], 0.0)
        v3 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2]) if g.dim == 3 else (p3[0] - p2[0], p3[1] - p2[1], 0.0)
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        dot = cx * v3[0] + cy * v3[1] + cz * v3[2]
        total += _sign(dot)
    return int(total)


def anomaly_check_one_generation() -> Tuple[int, int, int, int]:
    """
    Return integer anomaly sums (should be all zeros) from exp_sm_labeling_solver.
    """
    return sm.anomaly_checks_one_generation()


@dataclass(frozen=True)
class SU3RotationSummary:
    by_cycle_type: Dict[str, Tuple[int, float, float, float]]  # ct -> (count, mean_deg, min_deg, max_deg)


def su3_rotation_summary_from_anchor_holonomy() -> SU3RotationSummary:
    """
    Reproduce the S4-plaquette holonomy -> SO(3) rotation-angle summary used in the paper.
    This is currently anchored at the 2D 8x8 grid (n_bits=3) and is dimension-agnostic.
    """
    B = su3rep.basis_B()
    hols = su3rep.plaquette_holonomies()
    buckets: Dict[str, List[float]] = {}
    for p in hols:
        ct = holo.cycle_type(p)
        R = su3rep.su3_rep(p, B=B)
        ang = su3rep.rotation_angle_deg(R)
        buckets.setdefault(ct, []).append(float(ang))
    out: Dict[str, Tuple[int, float, float, float]] = {}
    for ct, xs in buckets.items():
        out[ct] = (len(xs), sum(xs) / float(len(xs)), min(xs), max(xs))
    return SU3RotationSummary(by_cycle_type=out)


def spin_half_proxy_from_su3_angles(summary: SU3RotationSummary) -> Optional[float]:
    """
    Minimal proxy: return the fraction of plaquettes whose induced SO(3) rotation angle
    is close to 180 degrees (pi-rotation), which is the simplest nontrivial double-cover witness.

    This is NOT a full spin-structure proof; it is a coarse diagnostic aligned with the paper's
    holonomy-to-candidate-family route.
    """
    total = 0
    pi_like = 0
    for _ct, (cnt, mean_deg, _mn, _mx) in summary.by_cycle_type.items():
        total += int(cnt)
        if abs(float(mean_deg) - 180.0) < 1e-6:
            pi_like += int(cnt)
    if total <= 0:
        return None
    return float(pi_like) / float(total)

