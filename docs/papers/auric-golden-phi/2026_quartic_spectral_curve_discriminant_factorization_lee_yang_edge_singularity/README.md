# Quartic Lee--Yang Spectral Curve (Discriminant, Branch Locus, Limit Laws)

This directory contains the source files for the manuscript and a reproducible certificate chain.

## 0) Environment

- `latexmk`/`pdflatex` (for `main.tex`)
- `perl` (for certificate scripts)
- `node` (for figure data generation)

## 1) Build the paper

From this directory:

```powershell
powershell -File .\scripts\build_paper.ps1
```

Keep intermediate files:

```powershell
powershell -File .\scripts\build_paper.ps1 -KeepAux
```

Output PDF:

- `main.pdf` in the current directory

## 2) Certification scripts

Run all with:

```powershell
perl .\scripts\branch_root_certificate.pl
perl .\scripts\coeff_nonneg_check.pl 5000
perl .\scripts\minimal_denominator_gcd_certificate.pl
```

Notes:

- `branch_root_certificate.pl`: exact checks of
  - `Disc(256 y^3+411 y^2+165 y+32) = -3^9*31^2*37<0`
  - rational sign enclosure for $\yLY\in(-1.13446,-1.13445)$.
- `coeff_nonneg_check.pl`: finite-range certificate for `a_{m,k}\ge 0` up to a user-specified bound.
- `minimal_denominator_gcd_certificate.pl`: symbolic elimination certificate for the transfer denominator coprimality.

## 3) Figure workflow (12 figures)

Generate all figure data:

```powershell
node .\scripts\generate_audit_figures.js
```

The script writes files under `figs/data/`:

- `fig01_branch_cubic_values.dat`
- `fig02_branch_roots_complex.dat`
- `fig03_root_moduli_real.dat`
- `fig04_local_collision_zoom.dat`
- `fig05_dominance_gap_real.dat`
- `fig06_zero_cloud_m12.dat`
- `fig07_zero_cloud_m20.dat`
- `fig08_zero_cloud_m28.dat`
- `fig09_zero_cloud_m36.dat`
- `fig10_eq12_contour.dat`
- `fig11_eq13_contour.dat`
- `fig12_eq23_contour.dat`
- `fig_generation_summary.txt`

Paper figures are rendered directly from these `.dat` files in
`sections/07_algorithms_and_certified_computation.tex`.

## 4) Notes

- `tmp_*.pl` files are scratch scripts and are ignored by git.
- If new visuals are needed, update only `scripts/generate_audit_figures.js` and re-run section 3.
