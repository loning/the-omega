# Draft: 2026 Golden Ratio Driven Scan–Projection Generation (Recursive Emergence)

## User Request (verbatim)
- Path: `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence`
- Goal: "研究统一相关问题"; academic tone; theorem-level rigor.
- Process constraints (user-stated): each round expects (i) new publishable conclusion, (ii) TeX modification, (iii) optional scripts/artifacts, (iv) next-round target.

## Planner Constraints (system)
- I can only produce *plans/drafts* (Markdown) under `.sisyphus/`.
- I cannot directly modify TeX/scripts or run commands; execution must be performed by the implementation agent via `/start-work`.

## Initial Context Observations (local scan; incomplete)
- Paper has `main.tex` with theorem/lemma/proposition/axiom/assumption/conjecture environments.
- There exists a significant scripts suite under `.../scripts/` generating `sections/generated/*.tex` and figures under `artifacts/export/` (exact inventory pending explore agent).
- The paper already contains a "统一闭环" statement: `sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part03d.tex` includes `\begin{theorem}[统一闭环：在线核—碰撞矩核—\zeta/primitive—几何维数谱]`.

## Confirmed Local Context (paper + pipeline)
- Build + reproducibility interface:
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/README.md`
  - One-click pipeline: `python3 scripts/run_all.py`.
  - Outputs:
    - `sections/generated/*.tex` (direct `\input{}` fragments)
    - `artifacts/export/*` (CSV/PNG/JSON evidence)

## Existing “Unify Correlation” Hooks Inside This Paper
- Unified closure theorem (already present):
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part03d.tex`
  - Thm. `thm:pom-unified-closure` links: online kernel (time defect) → moment-kernel (Renyi spectrum) → zeta/primitive (orbit extraction) → geometric spectrum.
- Correlation/mixing scale already defined from twisted spectral ratio:
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/09_zeta_finite_part/09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_a.tex`
  - Remark `cor:arity-335-collision-mixing-scale` defines `tau_mix := 1/(-log(rho/lambda))`.
- Time-correlation decay from spectral gap (transfer-operator view):
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part04.tex`
  - Prop. `prop:pom-time-corr-gap` gives an auditable exponential envelope in terms of `rho(theta) = Lambda(theta)/lambda_1(theta)`.

## Current Direction (confirmed)

- The previously sketched "rotation discrepancy -> folded histogram TV certificate" is already present in
  `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/12_experiments.tex`.
- Focus shifted to a genuinely new theorem-level bridge: identify the Chebotarev/Dirichlet worst twist ratio
  `eta_m := max_{chi!=1} rho(M_{m,chi})/rho(M_{m,1})` as the true time-correlation decay rate for residue-fiber observables
  on the lifted system (state x congruence fiber) under the Parry x Haar equilibrium.
- Execution-ready plan saved at: `.sisyphus/plans/auric-golden-phi-unified-correlation.md`.

## Candidate New Theorem (publishable; recommended focus)

### Rotation Discrepancy ⇒ Folded Histogram TV Certificate

Goal: make the “rotation scan vs Parry baseline” comparison theorem-level by splitting (i) *finite-sample/coverage* error from (ii) *model mismatch* error.

Core statement sketch (intended insertion: `sections/04_statistical_stability.tex` near the multiscale-residual audit, or `sections/12_experiments.tex` as a certificate lemma):

1) (Sturmian cylinder intervals) For a 2-interval coding of an irrational rotation, each length-`m` factor `w` corresponds to a (half-open) interval `I_w ⊂ [0,1)`. Hence for Kronecker points `x_t = x_0 + t alpha (mod 1)`:

`|freq_N(w) - Leb(I_w)| <= 2 D_N^*`,

where `D_N^*` is the 1D star discrepancy of `{x_t}_{t=0}^{N-1}`.

2) (Total-variation bound) Since the number of nonempty length-`m` Sturmian factors equals `m+1`,

`D_TV( pi_hat_{m,N}, pi_m^{rot} ) <= (m+1) D_N^*`.

3) (Fold pushforward contraction) For any measurable map `Fold_m`:

`D_TV( (Fold_m)_* pi_hat_{m,N}, (Fold_m)_* pi_m^{rot} ) <= (m+1) D_N^*`.

4) (Parry comparison decomposition)

`D_TV( (Fold_m)_* pi_hat_{m,N}, pi_m^{Parry} ) <= (m+1) D_N^* + D_TV( (Fold_m)_* pi_m^{rot}, pi_m^{Parry} )`.

This yields a completely auditable finite-sample certificate in terms of `D_N^*` (which is already computed in `scripts/exp_rotation_fold_vs_parry.py`).

## External Bridge Literature (projection/sampling/correlation)
- Tomography sampling / completeness:
  - Natterer, *The Mathematics of Computerized Tomography* (SIAM). DOI: 10.1137/1.9780898719284
  - Tuy (cone-beam completeness). DOI: 10.1137/0143035
  - Rattey–Lindgren (2D Radon sampling). DOI: 10.1109/TASSP.1981.1163686
- Spherical/angle sampling + discrepancy/energy bridges:
  - Stolarsky invariance principle (L2 cap discrepancy ↔ pairwise distance energy). DOI: 10.1090/S0002-9939-1972-0303418-3
  - QMC designs on the sphere (RKHS/Sobolev worst-case error ↔ kernel energy). DOI: 10.1090/S0025-5718-2014-02839-1
  - Landau necessary density for stable sampling. DOI: 10.1007/BF02395039

## Reproducibility Upgrade (if we choose to add evidence)
- Extend `scripts/exp_rotation_fold_vs_parry.py` to compute and export the certificate bound `(m+1) * D_N^*` alongside the measured `D_TV` between empirical folded histogram and the target baseline.
- Generate `sections/generated/tab_rotation_discrepancy_tv_certificate.tex` and cite it as a theorem-level “finite-sample envelope check”.

## Open Questions
- What exactly is meant by "统一相关问题" in this iteration: unify which objects/metrics/levels (e.g., discrepancy/correlation vs reconstruction error; multi-kernel unification; profinite axis unification; etc.)?
- Deliverable preference: strengthen an existing "统一闭环" theorem to a fully proved theorem chain, or introduce a genuinely new theorem beyond current statements?
- Verification expectations: purely theoretical, or must include reproducible computational evidence (generated tables/figures)?

## Scope Boundaries (tentative)
- INCLUDE: theorem-level formal statements + proof skeletons + exact insertion points in TeX; cross-link to existing definitions/lemmas.
- EXCLUDE (unless requested): new physical semantics claims; any claim requiring experimental data not present in repo.
