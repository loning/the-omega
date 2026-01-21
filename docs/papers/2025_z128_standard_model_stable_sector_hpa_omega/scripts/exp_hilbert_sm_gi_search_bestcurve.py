# -*- coding: utf-8 -*-
"""
Graph-isomorphism oriented search: find 2D/3D center-graphs (under the same m-schedule)
whose canonical signatures match, under a tiered relaxation of geometry constraints.

If no exact match is found within the budget, report the best candidates by physics score.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common_paths import figures_dir
from common_progress import ProgressEvery

from hilbert_sm_center_graph import BuildConstraints, build_center_graph_fixed
from hilbert_sm_canonical import canonical_signature_center_graph, canonical_signature_type_transition_graph
from hilbert_sm_schedule_search import sample_hierarchical_schedule, schedule_stats
from hilbert_sm_invariants import (
    anomaly_check_one_generation,
    score_physics_chirality_alignment,
)


def refined_ks(sched: Dict[int, int]) -> List[int]:
    return sorted([int(k) for k, m in sched.items() if int(m) > 6])


def tiers() -> List[Tuple[str, BuildConstraints]]:
    # Search in relaxed->strict order for quicker matches.
    return [
        ("edge_types_off_noncrossing_off", BuildConstraints(False, False, False)),
        ("allow_crossing_xy", BuildConstraints(True, False, True)),
        ("allow_pass_through_centers", BuildConstraints(True, True, False)),
        ("strict", BuildConstraints(True, True, True)),
    ]


def sample_choice(rng: random.Random, ks: List[int], n_opts: int) -> Dict[int, int]:
    return {int(k): int(rng.randrange(int(n_opts))) for k in ks}


def try_candidate(
    *,
    sched: Dict[int, int],
    ks_ref: List[int],
    tier_name: str,
    cons: BuildConstraints,
    choice2: Dict[int, int],
    choice3: Dict[int, int],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "tier": tier_name,
        "constraints": asdict(cons),
        "ok2": False,
        "ok3": False,
        "sig_equal": False,
    }
    try:
        g2 = build_center_graph_fixed(dim=2, m_by_k=sched, chosen_micro_option=choice2, max_micro_orders=16, constraints=cons)
        sig2, wl2 = canonical_signature_center_graph(g2, include_scan_pos=False, include_dim=False)
        sig2_type = canonical_signature_type_transition_graph(g2)
        sc2 = score_physics_chirality_alignment(g2)
        out.update(
            {
                "ok2": True,
                "sig2": sig2,
                "sig2_type": sig2_type,
                "wl2": {"rounds": wl2.n_rounds, "n_colors": wl2.n_colors},
                "score2": sc2.score,
                "detail2": sc2.details,
                "choice2": {str(k): int(choice2.get(k, 0)) for k in ks_ref},
            }
        )
    except Exception as e:  # noqa: BLE001
        out["err2"] = repr(e)

    try:
        g3 = build_center_graph_fixed(dim=3, m_by_k=sched, chosen_micro_option=choice3, max_micro_orders=48, constraints=cons)
        sig3, wl3 = canonical_signature_center_graph(g3, include_scan_pos=False, include_dim=False)
        sig3_type = canonical_signature_type_transition_graph(g3)
        sc3 = score_physics_chirality_alignment(g3)
        out.update(
            {
                "ok3": True,
                "sig3": sig3,
                "sig3_type": sig3_type,
                "wl3": {"rounds": wl3.n_rounds, "n_colors": wl3.n_colors},
                "score3": sc3.score,
                "detail3": sc3.details,
                "choice3": {str(k): int(choice3.get(k, 0)) for k in ks_ref},
            }
        )
    except Exception as e:  # noqa: BLE001
        out["err3"] = repr(e)

    if out.get("ok2") and out.get("ok3"):
        out["sig_equal"] = bool(out.get("sig2") == out.get("sig3"))
        out["sig_equal_type"] = bool(out.get("sig2_type") == out.get("sig3_type"))
        out["score_sum"] = float(out.get("score2", 0.0)) + float(out.get("score3", 0.0))
    return out


def main() -> None:
    a1, a2, a3, ag = anomaly_check_one_generation()
    if (a1, a2, a3, ag) != (0, 0, 0, 0):
        raise RuntimeError(f"Anomaly gate failed unexpectedly: {(a1, a2, a3, ag)}")

    out_root = figures_dir() / "adaptive" / "sm_hilbert_isomorphism"
    out_data = out_root / "data"
    out_data.mkdir(parents=True, exist_ok=True)

    tier_list = tiers()

    # Budget: keep within ~10 minutes; deterministic seeds.
    # (schedule + micro) search explodes quickly, so keep this modest and iterate.
    seeds = list(range(10))
    schedules_per_seed = 10
    micro_samples_per_schedule = 20
    time_limit_s = 570.0

    total_jobs = len(tier_list) * len(seeds) * schedules_per_seed * micro_samples_per_schedule
    pe = ProgressEvery(label="exp_sm_hilbert_gi_search_bestcurve", total=total_jobs, interval_s=60.0)
    pe.start()

    best_by_tier: Dict[str, Optional[Dict[str, Any]]] = {name: None for (name, _) in tier_list}
    best_match: Optional[Dict[str, Any]] = None
    best_match_type: Optional[Dict[str, Any]] = None
    best_sched_by_tier: Dict[str, Optional[Dict[str, Any]]] = {name: None for (name, _) in tier_list}

    t0 = time.time()
    job_i = 0
    for (tier_name, cons) in tier_list:
        for seed in seeds:
            rng = random.Random(int(seed))
            for si in range(schedules_per_seed):
                # Focus schedule sampling on the historically-refined window to keep feasibility.
                sched = sample_hierarchical_schedule(rng, k_lo=18, k_hi=52)
                ks_ref = refined_ks(sched)
                sst = schedule_stats(sched, k_min=18, k_max=52)
                for _ in range(micro_samples_per_schedule):
                    if (time.time() - t0) > time_limit_s:
                        break
                    pe.maybe(job_i, extra=f"tier={tier_name} seed={seed} sch={si} chg={sst.n_changed} sw={sst.n_switches} maxm={sst.max_m}")
                    job_i += 1
                    choice2 = sample_choice(rng, ks_ref, n_opts=16)
                    choice3 = sample_choice(rng, ks_ref, n_opts=48)
                    cand = try_candidate(sched=sched, ks_ref=ks_ref, tier_name=tier_name, cons=cons, choice2=choice2, choice3=choice3)
                    cand["m_schedule_by_k"] = {str(k): int(v) for k, v in sorted(sched.items())}
                    cand["schedule_stats_18_52"] = asdict(sst)

                    # record best by score_sum (requires both ok)
                    if cand.get("ok2") and cand.get("ok3"):
                        prev = best_by_tier.get(tier_name)
                        if prev is None or float(cand.get("score_sum", float("-inf"))) > float(prev.get("score_sum", float("-inf"))):
                            best_by_tier[tier_name] = cand
                            best_sched_by_tier[tier_name] = {"m_schedule_by_k": cand["m_schedule_by_k"], "schedule_stats_18_52": cand["schedule_stats_18_52"]}

                    # record first exact match (or the best-scoring among matches)
                    if cand.get("sig_equal"):
                        if best_match is None or float(cand.get("score_sum", float("-inf"))) > float(best_match.get("score_sum", float("-inf"))):
                            best_match = cand
                        # Early stop once we have a strict full-graph match.
                        break

                    # Also track best match at the coarse type-transition layer (diagnostic only).
                    if cand.get("sig_equal_type"):
                        if best_match_type is None or float(cand.get("score_sum", float("-inf"))) > float(best_match_type.get("score_sum", float("-inf"))):
                            best_match_type = cand
                if best_match is not None:
                    break
                if (time.time() - t0) > time_limit_s:
                    break
            if best_match is not None:
                break
            if (time.time() - t0) > time_limit_s:
                break
        if best_match is not None:
            break
        if (time.time() - t0) > time_limit_s:
            break

    report = {
        "anomaly_one_generation_Ynum": {"su3su3u1": a1, "su2su2u1": a2, "u1u1u1": a3, "gravgravu1": ag},
        "search_budget": {
            "seeds": seeds,
            "schedules_per_seed": schedules_per_seed,
            "micro_samples_per_schedule": micro_samples_per_schedule,
            "total_jobs": total_jobs,
        },
        "best_by_tier": best_by_tier,
        "best_schedule_by_tier": best_sched_by_tier,
        "best_match_signature_equal_full": best_match,
        "best_match_signature_equal_type": best_match_type,
        "wall_clock_seconds": time.time() - t0,
        "completed_jobs": job_i,
    }

    out_json = out_data / "sm_hilbert_gi_search_bestcurve_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    pe.done(extra=f"wrote {out_json}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

