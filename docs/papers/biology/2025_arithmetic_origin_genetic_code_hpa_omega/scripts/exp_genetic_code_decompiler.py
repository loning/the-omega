# -*- coding: utf-8 -*-
"""
Reproducible experiments for:
  - scanning 24 nucleotide two-bit encodings,
  - identifying the unique encoding mu* by start/stop boundary homology,
  - generating LaTeX fragments in sections/generated/,
  - generating full codon tables and spectrum summaries under mu*.

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from genetic_code_tools import (
    BOUNDARY_INT_SET,
    BOUNDARY_WORDS,
    GENETIC_CODE,
    STOP_CODONS,
    all_encodings,
    amino_acid_spectrum,
    encoding_to_str,
    fold6,
    fold_codon,
    hydrophobicity_correlation_under_mu,
    mutual_information_bits,
    satisfies_start_stop_boundary_homology,
    vmean_hydrophobicity_correlation_under_mu,
    vmean_mass_correlation_under_mu,
    zeckendorf_value,
)


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def generate_stop_fine_structure(mu: dict[str, str]) -> None:
    rows = []
    for codon in STOP_CODONS:
        f = fold_codon(codon, mu)
        if codon == "UAA":
            kind = "boundary stop"
        elif codon == "UAG":
            kind = "uplifted blocker"
        else:
            kind = "projection mismatch"
        rows.append(
            f"{codon} & \\texttt{{{f.bits}}} & {f.n} & \\texttt{{{f.w}}} & {f.v} & {f.delta} & {kind} \\\\"
        )
    # TeX Live 2025 note: placing \bottomrule immediately after \input{...} inside tabular
    # can trigger a "Misplaced \noalign" error. We therefore include \bottomrule inside
    # the generated fragment.
    write_text(generated_dir() / "stop_fine_structure_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")


def generate_boundary_sector_codons(mu: dict[str, str]) -> None:
    rows = []
    for codon, aa in sorted(GENETIC_CODE.items()):
        f = fold_codon(codon, mu)
        if f.n in BOUNDARY_INT_SET:
            # Identify the partner index within the same boundary word (uplift split).
            # For boundary words, the two preimages differ by 34.
            partner = f.n + 34 if (f.n + 34) in BOUNDARY_INT_SET else f.n - 34
            uplift_tag = f"{f.n}/{partner}"
            rows.append(f"{f.n} & {codon} & {aa} & \\texttt{{{f.w}}} & {uplift_tag} \\\\")
    rows.sort(key=lambda s: int(s.split(" & ", 1)[0]))
    write_text(generated_dir() / "boundary_sector_codons_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")


def generate_amino_acid_spectrum_rows(mu: dict[str, str]) -> None:
    spec = amino_acid_spectrum(mu)
    aas = sorted(spec.keys(), key=lambda k: (k == "Stop", k))
    rows = []
    for aa in aas:
        vmin = int(spec[aa]["V_min"])
        vmax = int(spec[aa]["V_max"])
        vset = spec[aa]["V_set"]
        vset_str = "\\{ " + ", ".join(str(x) for x in vset) + " \\}"
        rows.append(f"{aa} & {vmin} & {vmax} & ${vset_str}$ \\\\")
    write_text(generated_dir() / "amino_acid_spectrum_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")


def generate_full_codon_table_rows(mu: dict[str, str]) -> None:
    rows = []
    for codon, aa in sorted(GENETIC_CODE.items()):
        f = fold_codon(codon, mu)
        tags = []
        if f.w in BOUNDARY_WORDS:
            tags.append("BOUNDARY")
        if f.v == 0:
            tags.append("VACUUM")
        if f.v == 20:
            tags.append("MAX")
        tag_str = "|".join(tags) if tags else "-"
        rows.append(
            f"{aa} & {codon} & \\texttt{{{f.bits}}} & \\texttt{{{f.w}}} & {f.v} & {f.n} & {f.delta} & {tag_str} \\\\"
        )
    write_text(generated_dir() / "codon_full_table_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")


def generate_encoding_scan_summary() -> None:
    encs = all_encodings()
    stop_hits_hist = Counter()
    all_stop_in_boundary_int_set = 0
    homology_hits = []
    mi_values = []

    for mu in encs:
        mi_values.append(mutual_information_bits(mu))

        hits = 0
        stop_ns = []
        for codon in STOP_CODONS:
            n = fold_codon(codon, mu).n
            stop_ns.append(n)
            if fold_codon(codon, mu).w in BOUNDARY_WORDS:
                hits += 1
        stop_hits_hist[hits] += 1
        if all(n in BOUNDARY_INT_SET for n in stop_ns):
            all_stop_in_boundary_int_set += 1
        if satisfies_start_stop_boundary_homology(mu):
            homology_hits.append(mu)

    mi_min = min(mi_values)
    mi_max = max(mi_values)

    lines = []
    lines.append("\\paragraph{Encoding scan.}")
    lines.append(
        f"There are $24$ bijective two-bit encodings. Under the standard stop set $\\{{\\mathrm{{UAA,UAG,UGA}}\\}}$, "
        f"the number of stop codons landing in the boundary sector has histogram: "
        f"$\\{{0:{stop_hits_hist.get(0,0)},\\ 1:{stop_hits_hist.get(1,0)},\\ 2:{stop_hits_hist.get(2,0)},\\ 3:{stop_hits_hist.get(3,0)}\\}}$."
    )
    lines.append(
        "In particular, no encoding places all three stop codons inside the boundary sector, and the stronger RF boundary-index inclusion test "
        f"(``all stop $N\\in\\{{14,17,19,48,51,53\\}}$'') succeeds for {all_stop_in_boundary_int_set} encodings."
    )
    lines.append("")
    lines.append("\\paragraph{Start--stop boundary homology.}")
    lines.append(
        f"Exactly {len(homology_hits)} encoding satisfies start--stop boundary homology, namely "
        f"$A\\mapsto 00,\\ C\\mapsto 01,\\ G\\mapsto 10,\\ U\\mapsto 11$."
    )
    lines.append("")
    lines.append("\\paragraph{Mutual information diagnostic.}")
    lines.append(
        f"Under the uniform codon prior, the mutual information $I(\\mathsf{{Gen}}(C);w_\\mu(C))$ ranges from "
        f"${mi_min:.6f}$ to ${mi_max:.6f}$ bits across the $24$ encodings."
    )

    write_text(generated_dir() / "encoding_scan_summary.tex", "\n".join(lines) + "\n")


def _latex_encoding(mu: dict[str, str]) -> str:
    return (
        f"A\\mapsto \\texttt{{{mu['A']}}},\\ "
        f"C\\mapsto \\texttt{{{mu['C']}}},\\ "
        f"G\\mapsto \\texttt{{{mu['G']}}},\\ "
        f"U\\mapsto \\texttt{{{mu['U']}}}"
    )


def generate_mutual_information_summary() -> None:
    encs = all_encodings()

    best_mu = None
    best_mi = None
    mi_star = mutual_information_bits(MU_STAR)

    mi_pairs: list[tuple[float, dict[str, str]]] = []
    for mu in encs:
        mi = mutual_information_bits(mu)
        mi_pairs.append((mi, mu))
        if best_mi is None or mi > best_mi:
            best_mi = mi
            best_mu = mu

    assert best_mu is not None and best_mi is not None

    mi_pairs.sort(key=lambda t: t[0], reverse=True)
    top_k = 5
    top_lines = []
    for i, (mi, mu) in enumerate(mi_pairs[:top_k], start=1):
        tag = " ($\\mu^\\ast$)" if mu == MU_STAR else ""
        top_lines.append(f"{i}. ${mi:.6f}$ bits: ${_latex_encoding(mu)}${tag}")

    lines = []
    lines.append("\\paragraph{Mutual information details.}")
    lines.append(
        f"Under the uniform codon prior, the unique start--stop homology solution "
        f"$\\mu^\\ast$ has mutual information $I(\\mathsf{{Gen}}(C);w_{{\\mu^\\ast}}(C))={mi_star:.6f}$ bits."
    )
    lines.append(
        f"The maximum over all $24$ encodings is ${best_mi:.6f}$ bits, achieved by "
        f"$\\mu_\\mathrm{{MI}}$ given by ${_latex_encoding(best_mu)}$."
    )
    lines.append("")
    lines.append("\\noindent\\textbf{Top encodings by mutual information (descending):}")
    lines.append("\\begin{enumerate}")
    for s in top_lines:
        lines.append(f"\\item {s}")
    lines.append("\\end{enumerate}")
    lines.append("")

    write_text(generated_dir() / "mutual_information_summary.tex", "\n".join(lines) + "\n")

    brief = (
        f"Under the uniform codon prior, $I(\\mathsf{{Gen}}(C);w_{{\\mu^\\ast}}(C))={mi_star:.6f}$ bits, "
        f"while the maximum over all $24$ encodings is ${best_mi:.6f}$ bits (achieved by "
        f"$\\mu_\\mathrm{{MI}}$ with ${_latex_encoding(best_mu)}$)."
    )
    write_text(generated_dir() / "mutual_information_brief.tex", brief + "\n")


def generate_fold6_invariants_summary() -> None:
    """
    Encoding-independent Fold_6 invariants for N in {0,...,63}:
      - degeneracy histogram (preimage size -> number of outputs)
      - uplift (Delta_N := N - V(Fold_6(N))) value set
    Also record codon-level Delta distribution under mu* for convenience.
    """
    pre: dict[str, list[int]] = defaultdict(list)
    delta_n_hist: Counter[int] = Counter()

    for n in range(64):
        w = fold6(n)
        pre[w].append(n)
        delta_n = n - zeckendorf_value(w)
        delta_n_hist[delta_n] += 1

    deg_hist = Counter(len(v) for v in pre.values())

    # Codon-level uplift distribution under mu*
    delta_codon_hist: Counter[int] = Counter()
    for codon in sorted(GENETIC_CODE.keys()):
        f = fold_codon(codon, MU_STAR)
        delta_codon_hist[f.delta] += 1

    delta_values = sorted(delta_n_hist.keys())

    lines = []
    lines.append("\\paragraph{Fold\\_6 degeneracy (encoding-independent).}")
    lines.append(
        "For $\\mathrm{Fold}_6:\\{0,\\dots,63\\}\\twoheadrightarrow X_6$, the preimage size "
        "is always $2$, $3$, or $4$, with histogram "
        f"$\\{{2:{deg_hist.get(2,0)},\\ 3:{deg_hist.get(3,0)},\\ 4:{deg_hist.get(4,0)}\\}}$ over the $21$ outputs."
    )
    lines.append("")
    lines.append("\\paragraph{Uplift values at window length $6$ (encoding-independent).}")
    lines.append(
        "Define $\\Delta(N):=N-V(\\mathrm{Fold}_6(N))$. For $N\\in\\{0,\\dots,63\\}$, "
        "the possible uplift values are "
        f"$\\Delta(N)\\in\\{{{', '.join(str(x) for x in delta_values)}\\}}$, "
        "corresponding to Fibonacci weights $F_8=21$, $F_9=34$, and $F_{10}=55$ beyond the window."
    )
    lines.append(
        "The multiplicities over $\\{0,\\dots,63\\}$ are: "
        + ", ".join(f"$\\Delta={k}$: {delta_n_hist[k]}" for k in delta_values)
        + "."
    )
    lines.append("")
    lines.append("\\paragraph{Codon-level uplift distribution under $\\mu^\\ast$.}")
    lines.append(
        "Under the unique encoding $\\mu^\\ast$, the $64$ codons have uplift histogram: "
        + "$\\{"
        + ",\\ ".join(f"{k}:{delta_codon_hist.get(k,0)}" for k in delta_values)
        + "\\}$."
    )
    lines.append("")

    write_text(generated_dir() / "fold6_invariants_summary.tex", "\n".join(lines) + "\n")


def generate_hydrophobicity_correlation(mu: dict[str, str]) -> None:
    corr = hydrophobicity_correlation_under_mu(mu)
    n = int(corr["n"])
    r = corr["pearson_r"]
    p = corr["pearson_p"]
    rho = corr["spearman_rho"]
    p_rho = corr["spearman_p"]

    # Single LaTeX paragraph fragment used inline.
    s = (
        f"Pearson $r={r:.3f}$ ($p={p:.4f}$, $n={n}$) and "
        f"Spearman $\\rho={rho:.3f}$ ($p={p_rho:.4f}$, $n={n}$)."
    )
    write_text(generated_dir() / "hydrophobicity_correlation.tex", s + "\n")


def generate_vmean_property_correlations(mu: dict[str, str]) -> None:
    """
    Exploratory correlations using V_mean (uniform-codon average of V per amino acid).
    """
    corr_h = vmean_hydrophobicity_correlation_under_mu(mu)
    corr_m = vmean_mass_correlation_under_mu(mu)

    def fmt(c: dict[str, float]) -> tuple[str, str, str, str, int]:
        n = int(c["n"])
        r = c["pearson_r"]
        p = c["pearson_p"]
        rho = c["spearman_rho"]
        p_rho = c["spearman_p"]
        return f"{r:.3f}", f"{p:.4f}", f"{rho:.3f}", f"{p_rho:.4f}", n

    r_h, p_h, rho_h, p_rho_h, n_h = fmt(corr_h)
    r_m, p_m, rho_m, p_rho_m, n_m = fmt(corr_m)
    assert n_h == n_m

    lines = []
    lines.append(
        f"For $V_\\mathrm{{mean}}$ (uniform-codon average of $V$ per amino acid), "
        f"the correlations are: hydrophobicity Pearson $r={r_h}$ ($p={p_h}$, $n={n_h}$), "
        f"Spearman $\\rho={rho_h}$ ($p={p_rho_h}$); "
        f"mass Pearson $r={r_m}$ ($p={p_m}$, $n={n_m}$), "
        f"Spearman $\\rho={rho_m}$ ($p={p_rho_m}$)."
    )
    write_text(generated_dir() / "vmean_property_correlations.tex", "\n".join(lines) + "\n")


def main() -> None:
    print("=== Genetic code reverse compilation (Fold_6) ===")

    # 1) Unique encoding by start/stop boundary homology
    hits = [mu for mu in all_encodings() if satisfies_start_stop_boundary_homology(mu)]
    print("Start/stop boundary-homology encodings:", len(hits))
    for mu in hits:
        print("  hit:", encoding_to_str(mu))

    if hits != [MU_STAR]:
        raise AssertionError("Expected a unique mu* hit: A=00,C=01,G=10,U=11")

    # 2) Sanity checks for 14/48 symmetry
    aug = fold_codon("AUG", MU_STAR)
    uaa = fold_codon("UAA", MU_STAR)
    print("AUG:", aug)
    print("UAA:", uaa)
    if not (aug.n == 14 and uaa.n == 48 and aug.w == uaa.w == "100001"):
        raise AssertionError("14/48 symmetry check failed")

    # 3) Generate LaTeX fragments
    generate_stop_fine_structure(MU_STAR)
    generate_boundary_sector_codons(MU_STAR)
    generate_amino_acid_spectrum_rows(MU_STAR)
    generate_full_codon_table_rows(MU_STAR)
    generate_encoding_scan_summary()
    generate_mutual_information_summary()
    generate_fold6_invariants_summary()
    generate_hydrophobicity_correlation(MU_STAR)
    generate_vmean_property_correlations(MU_STAR)

    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


