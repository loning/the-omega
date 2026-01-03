# -*- coding: utf-8 -*-
"""
Reproducible experiments for:
  - scanning 24 nucleotide two-bit encodings,
  - identifying the unique encoding mu* by control-boundary alignment on K={AUG,UAA,UAG,UGA},
  - generating LaTeX fragments in sections/generated/,
  - generating full codon tables and spectrum summaries under mu*.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import itertools
from collections import Counter, defaultdict
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import (
    BOUNDARY_INT_SET,
    BOUNDARY_WORDS,
    GENETIC_CODE,
    STOP_CODONS,
    all_encodings,
    amino_acid_spectrum,
    encoding_to_str,
    find_orfs,
    fold6,
    fold_codon,
    hydrophobicity_correlation_under_mu,
    iter_fasta,
    mutual_information_bits,
    satisfies_start_stop_boundary_homology,
    vmean_hydrophobicity_correlation_under_mu,
    vmean_mass_correlation_under_mu,
    zeckendorf_value,
)


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 6


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _fingerprint_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    st = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genetic code reverse compilation (Fold_6) + LaTeX fragments")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


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

def generate_control_codons_table(mu: dict[str, str]) -> None:
    """
    Table for the control set K={AUG,UAA,UAG,UGA}.
    """
    control_codons = ("AUG", "UAA", "UAG", "UGA")
    rows = []
    for codon in control_codons:
        f = fold_codon(codon, mu)
        is_b = "yes" if f.w in BOUNDARY_WORDS else "no"
        rows.append(
            f"{codon} & \\texttt{{{f.bits}}} & {f.n} & \\texttt{{{f.w}}} & {f.v} & {f.delta} & {is_b} \\\\"
        )
    write_text(generated_dir() / "control_codons_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")


def generate_human_transcript_case_studies(mu: dict[str, str]) -> None:
    """
    Reproducible case studies on two human transcripts:
      - HBB (RefSeq NM_000518.5)
      - INS (Ensembl ENST00000381330.5)
    Requires FASTA files under data/.
    """
    data_dir = root_dir() / "data"
    cases = [
        ("HBB", "NM_000518.5", data_dir / "NM_000518.5.fasta"),
        ("INS", "ENST00000381330.5", data_dir / "ENST00000381330.5.fasta"),
    ]

    rows: list[str] = []
    for gene, tid, path in cases:
        if not path.exists():
            continue
        records = list(iter_fasta(str(path)))
        if not records:
            continue
        rid, seq = records[0]
        nt_len = len(seq)

        # Choose the longest ORF across all three reading frames (robust to UTRs and frame offset).
        best = None  # (length_codons_including_stop, start, stop, frame)
        for frame in (0, 1, 2):
            orfs = find_orfs(seq, frame=frame, min_codons=0)
            for start, stop in orfs:
                length_codons = (stop - start) // 3 + 1
                cand = (length_codons, start, stop, frame)
                if best is None or cand > best:
                    best = cand
        if best is None:
            continue
        length_codons, start, stop, frame = best
        start_codon = seq[start : start + 3]
        stop_codon = seq[stop : stop + 3]

        f_start = fold_codon(start_codon, mu)
        f_stop = fold_codon(stop_codon, mu)

        # 1-based base positions to match typical transcript coordinates.
        start_1 = start + 1
        stop_1 = stop + 1

        start_tuple = f"({f_start.n},\\mathtt{{{f_start.w}}},{f_start.v},{f_start.delta})"
        stop_tuple = f"({f_stop.n},\\mathtt{{{f_stop.w}}},{f_stop.v},{f_stop.delta})"

        rows.append(
            f"{gene} (\\path{{{tid}}}) & {nt_len} & {length_codons} & {frame} & {start_1} & {stop_1} & {stop_codon} & ${start_tuple}$ & ${stop_tuple}$ \\\\"
        )

    write_text(generated_dir() / "human_transcript_case_studies_rows.tex", "\n".join(rows) + "\n\\bottomrule\n")

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
            tags.append("MIN")
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
    control_hits_hist = Counter()
    control_hits_max = 0
    control_best_mus: list[dict[str, str]] = []
    mi_values = []

    for mu in encs:
        mi_values.append(mutual_information_bits(mu))

        # Control-boundary alignment score over K={AUG,UAA,UAG,UGA}.
        control_codons = ("AUG", "UAA", "UAG", "UGA")
        control_hits = 0
        for c in control_codons:
            if fold_codon(c, mu).w in BOUNDARY_WORDS:
                control_hits += 1
        control_hits_hist[control_hits] += 1
        if control_hits > control_hits_max:
            control_hits_max = control_hits
            control_best_mus = [mu]
        elif control_hits == control_hits_max:
            control_best_mus.append(mu)

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

    # Brief fragment for the main Results section (control objective only).
    brief = []
    brief.append(
        f"Under the control set $\\mathcal{{K}}=\\{{\\mathrm{{AUG,UAA,UAG,UGA}}\\}}$, "
        f"the score histogram is $\\{{0:{control_hits_hist.get(0,0)},\\ 1:{control_hits_hist.get(1,0)},\\ 2:{control_hits_hist.get(2,0)}\\}}$ over $24$ encodings. "
        f"The maximum is $S_{{\\max}}={control_hits_max}$, achieved by a unique encoding: "
        f"${_latex_encoding(control_best_mus[0])}$. "
        f"Under the uniform encoding prior this is a one-in-24 event."
    )
    write_text(generated_dir() / "control_objective_brief.tex", "\n".join(brief) + "\n")

    lines = []
    lines.append("\\paragraph{Encoding scan.}")
    lines.append(
        f"There are $24$ bijective two-bit encodings. Under the standard stop set $\\{{\\mathrm{{UAA,UAG,UGA}}\\}}$, "
        f"the number of stop codons landing in the boundary sector has histogram: "
        f"$\\{{0:{stop_hits_hist.get(0,0)},\\ 1:{stop_hits_hist.get(1,0)},\\ 2:{stop_hits_hist.get(2,0)},\\ 3:{stop_hits_hist.get(3,0)}\\}}$."
    )
    lines.append(
        f"Under the control set $\\mathcal{{K}}=\\{{\\mathrm{{AUG,UAA,UAG,UGA}}\\}}$, "
        f"the boundary-hit score $S(\\mu)$ has histogram: "
        f"$\\{{0:{control_hits_hist.get(0,0)},\\ 1:{control_hits_hist.get(1,0)},\\ 2:{control_hits_hist.get(2,0)},\\ 3:{control_hits_hist.get(3,0)},\\ 4:{control_hits_hist.get(4,0)}\\}}$."
    )
    lines.append(
        f"The maximum is $S_{{\\max}}={control_hits_max}$, achieved by {len(control_best_mus)} encoding."
        + (" " if len(control_best_mus) == 1 else "s ")
        + (f"Namely ${_latex_encoding(control_best_mus[0])}$." if len(control_best_mus) == 1 else "")
    )
    lines.append(
        "In particular, no encoding places all three stop codons inside the boundary sector, and the stronger RF boundary-index inclusion test "
        f"(``all stop $N\\in\\{{14,17,19,48,51,53\\}}$'') succeeds for {all_stop_in_boundary_int_set} encodings."
    )
    lines.append("")
    lines.append("\\paragraph{Emergent start--stop boundary homology.}")
    lines.append(
        f"Exactly {len(homology_hits)} encoding satisfies start--stop boundary homology "
        f"($w_\\mu(\\mathrm{{AUG}})=w_\\mu(\\mathrm{{UAA}})\\in X_6^\\mathrm{{bdry}}$), "
        f"namely $A\\mapsto 00,\\ C\\mapsto 01,\\ G\\mapsto 10,\\ U\\mapsto 11$."
    )
    lines.append("")
    lines.append("\\paragraph{Mutual information diagnostic.}")
    lines.append(
        f"Under the uniform codon prior, the mutual information $I(\\mathsf{{Gen}}(C);w_\\mu(C))$ ranges from "
        f"${mi_min:.6f}$ to ${mi_max:.6f}$ bits across the $24$ encodings."
    )

    write_text(generated_dir() / "encoding_scan_summary.tex", "\n".join(lines) + "\n")


def generate_encoding_scan_table() -> None:
    """
    Full table over all 24 encodings with key diagnostics:
      - control-boundary score S(mu) over K={AUG,UAA,UAG,UGA}
      - number of stop codons landing in X6^bdry
      - start/stop boundary homology flag
      - mutual information I(Gen(C); w_mu(C)) under uniform codon prior
    """
    encs = all_encodings()
    control_codons = ("AUG", "UAA", "UAG", "UGA")

    # Identify the MI-optimal encoding for tagging in the table.
    best_mu_mi: dict[str, str] | None = None
    best_mi = None
    for mu in encs:
        mi = float(mutual_information_bits(mu))
        if best_mi is None or mi > best_mi:
            best_mi = mi
            best_mu_mi = mu
    assert best_mu_mi is not None and best_mi is not None

    rows: list[dict[str, object]] = []
    for mu in encs:
        s = sum(1 for c in control_codons if fold_codon(c, mu).w in BOUNDARY_WORDS)
        stop_b = sum(1 for c in STOP_CODONS if fold_codon(c, mu).w in BOUNDARY_WORDS)
        hom = bool(satisfies_start_stop_boundary_homology(mu))
        mi = float(mutual_information_bits(mu))
        tag = "-"
        if mu == MU_STAR:
            tag = "$\\mu^\\ast$"
        elif mu == best_mu_mi:
            tag = "$\\mu_{\\mathrm{MI}}$"
        rows.append(
            {
                "mu": mu,
                "S": int(s),
                "stopB": int(stop_b),
                "hom": bool(hom),
                "mi": float(mi),
                "tag": str(tag),
            }
        )

    rows.sort(key=lambda r: (-int(r["S"]), -int(bool(r["hom"])), -float(r["mi"]), _latex_encoding(r["mu"])))

    tbl: list[str] = []
    tbl.append("\\begin{center}")
    tbl.append("\\scriptsize")
    tbl.append("\\setlength{\\tabcolsep}{3pt}")
    tbl.append("\\renewcommand{\\arraystretch}{1.10}")
    tbl.append("\\resizebox{\\textwidth}{!}{%")
    tbl.append("\\begin{tabular}{rccccrrcrl}")
    tbl.append("\\toprule")
    tbl.append("rank & $A$ & $C$ & $G$ & $U$ & $S(\\mu)$ & stopB & homology & $I$ (bits) & tag \\\\")
    tbl.append("\\midrule")
    for i, r in enumerate(rows, start=1):
        mu = r["mu"]
        assert isinstance(mu, dict)
        a = mu["A"]
        c = mu["C"]
        g = mu["G"]
        u = mu["U"]
        s = int(r["S"])
        stop_b = int(r["stopB"])
        hom = "yes" if bool(r["hom"]) else "no"
        mi = float(r["mi"])
        tag = str(r["tag"])
        tbl.append(
            f"{i} & \\texttt{{{a}}} & \\texttt{{{c}}} & \\texttt{{{g}}} & \\texttt{{{u}}} & {s} & {stop_b} & {hom} & {mi:.6f} & {tag} \\\\"
        )
    tbl.append("\\bottomrule")
    tbl.append("\\end{tabular}")
    tbl.append("}")
    tbl.append("\\end{center}")
    tbl.append("")

    write_text(generated_dir() / "encoding_scan_table.tex", "\n".join(tbl) + "\n")


def _codon_bitmask_index() -> tuple[list[str], dict[str, int]]:
    """
    Return (codons_sorted, codon_to_bit_index) where each codon maps to a distinct bit position in [0,63].
    """
    codons = sorted(GENETIC_CODE.keys())
    if len(codons) != 64:
        raise AssertionError("Expected 64 codons in GENETIC_CODE")
    return codons, {c: i for i, c in enumerate(codons)}


def generate_control_objective_null_over_all_4codon_sets() -> None:
    """
    Exact null enumeration over all 4-codon subsets K of the 64-codon alphabet.

    For each K with |K|=4, define the boundary-hit objective:
      S_K(mu) = sum_{c in K} 1{w_mu(c) in X6^bdry}
    and report:
      S_max(K) = max_mu S_K(mu), and M(K) = #argmax encodings (out of 24).
    """
    codons, bit_idx = _codon_bitmask_index()

    # Precompute boundary masks (one per encoding).
    encs = all_encodings()
    boundary_masks: list[int] = []
    for mu in encs:
        m = 0
        for c in codons:
            if fold_codon(c, mu).w in BOUNDARY_WORDS:
                m |= 1 << bit_idx[c]
        # Each encoding has exactly 6 boundary codons (2 per boundary word).
        if m.bit_count() != 6:
            raise AssertionError("Unexpected boundary codon count under an encoding")
        boundary_masks.append(int(m))
    if len(boundary_masks) != 24:
        raise AssertionError("Expected 24 encodings")

    # Control set of interest.
    control_codons = ("AUG", "UAA", "UAG", "UGA")
    control_mask = 0
    for c in control_codons:
        control_mask |= 1 << bit_idx[c]

    def _score_mask(kmask: int) -> tuple[int, int, int | None]:
        best = -1
        n_best = 0
        for bm in boundary_masks:
            s = int((bm & kmask).bit_count())
            if s > best:
                best = s
                n_best = 1
            elif s == best:
                n_best += 1
        # Re-scan to recover the unique argmax index only when needed; avoid storing indices in the loop above
        # (keeps the objective implementation simple and auditable).
        if n_best != 1:
            return int(best), int(n_best), None
        # Find the unique argmax encoding index.
        idx0: int | None = None
        for i, bm in enumerate(boundary_masks):
            if int((bm & kmask).bit_count()) == int(best):
                if idx0 is None:
                    idx0 = int(i)
                else:
                    # Should not happen when n_best==1, but keep it safe.
                    return int(best), int(n_best), None
        return int(best), int(n_best), idx0

    control_smax, control_m, control_best_idx = _score_mask(control_mask)
    if control_best_idx is None:
        raise AssertionError("Expected control set to have a unique argmax encoding")
    mu_star_idx = None
    for i, mu in enumerate(encs):
        if mu == MU_STAR:
            mu_star_idx = int(i)
            break
    if mu_star_idx is None:
        raise AssertionError("Failed to locate MU_STAR among encodings")

    # Enumerate all 4-codon subsets (C(64,4)=635,376).
    total = 0
    counts_by_smax: Counter[int] = Counter()
    unique_by_smax: Counter[int] = Counter()
    mu_star_unique = 0  # mu* is the unique maximizer (any S_max)
    mu_star_unique_smax2 = 0  # mu* is the unique maximizer with S_max=2

    for a, b, c, d in itertools.combinations(range(64), 4):
        kmask = (1 << a) | (1 << b) | (1 << c) | (1 << d)
        smax, m, best_idx = _score_mask(kmask)
        total += 1
        counts_by_smax[int(smax)] += 1
        if int(m) == 1:
            unique_by_smax[int(smax)] += 1
            if best_idx is not None and int(best_idx) == int(mu_star_idx):
                mu_star_unique += 1
                if int(smax) == int(control_smax):
                    mu_star_unique_smax2 += 1

    if total != 635_376:
        raise AssertionError(f"Unexpected total 4-codon subsets: {total}")

    # Summary paragraph.
    # Secondary null: fix the standard stop set and vary the "start" codon choice.
    stop_set = ("UAA", "UAG", "UGA")
    stop_mask = 0
    for c in stop_set:
        stop_mask |= 1 << bit_idx[c]
    start_candidates = [c for c in codons if c not in stop_set]
    if len(start_candidates) != 61:
        raise AssertionError("Expected 61 non-stop codons")

    fixed_dist: Counter[int] = Counter()
    fixed_unique = 0
    fixed_unique_mu_star: list[str] = []
    fixed_unique_rows: list[tuple[str, int, dict[str, str]]] = []

    for s in start_candidates:
        kmask = int(stop_mask | (1 << bit_idx[s]))
        smax, m, best_idx = _score_mask(kmask)
        fixed_dist[int(smax)] += 1
        if int(m) == 1:
            fixed_unique += 1
            # Identify the unique argmax encoding.
            if best_idx is None:
                continue
            best_mu = encs[int(best_idx)]
            fixed_unique_rows.append((str(s), int(smax), best_mu))
            if best_mu == MU_STAR:
                fixed_unique_mu_star.append(str(s))

    fixed_unique_mu_star.sort()

    s_lines: list[str] = []
    s_lines.append(
        "Exact null enumeration over all $4$-codon subsets $\\mathcal{K}\\subset\\Sigma^3$ "
        f"($\\binom{{64}}{{4}}={total}$). "
        "For each $\\mathcal{K}$ we maximize the boundary-hit objective "
        "$S_{\\mathcal{K}}(\\mu)=\\sum_{c\\in\\mathcal{K}}\\mathbf{1}\\{w_\\mu(c)\\in X_6^{\\mathrm{bdry}}\\}$ "
        "over the $24$ encodings, and record $S_{\\max}(\\mathcal{K})$ and the argmax multiplicity "
        "$M(\\mathcal{K})=\\#\\arg\\max_{\\mu} S_{\\mathcal{K}}(\\mu)$. "
        f"For the biological control set $\\{{\\mathrm{{AUG,UAA,UAG,UGA}}\\}}$, "
        f"we have $S_{{\\max}}={control_smax}$ with $M={control_m}$ and the unique maximizer equals $\\mu^\\ast$."
    )
    s_lines.append("")
    s_lines.append(
        f"Under the same uniform $4$-codon subset prior, $\\mu^\\ast$ is the \\emph{{unique}} maximizer for "
        f"{mu_star_unique}/{total} subsets (probability {mu_star_unique/float(total):.6f})."
    )
    s_lines.append(
        f"Restricting to the maximal-score class $S_{{\\max}}=2$, $\\mu^\\ast$ is the unique maximizer for "
        f"{mu_star_unique_smax2}/{total} subsets (probability {mu_star_unique_smax2/float(total):.6f})."
    )
    s_lines.append("")
    s_lines.append(
        "Stop-fixed null (more structured): fixing the standard stop set "
        "$\\{\\mathrm{UAA,UAG,UGA}\\}$ and varying a single additional codon over the $61$ non-stop choices, "
        f"the argmax over encodings is unique for {fixed_unique}/61 choices. "
        f"Among those, the unique argmax equals $\\mu^\\ast$ for "
        f"{len(fixed_unique_mu_star)}/61 choices (namely "
        + (", ".join(f"$\\mathrm{{{c}}}$" for c in fixed_unique_mu_star) if fixed_unique_mu_star else "none")
        + ")."
    )
    write_text(generated_dir() / "control_objective_null_summary.tex", "\n".join(s_lines) + "\n")

    # Compact table: distribution by S_max and uniqueness rate.
    tbl: list[str] = []
    tbl.append("\\begin{center}")
    tbl.append("\\small")
    tbl.append("\\setlength{\\tabcolsep}{6pt}")
    tbl.append("\\renewcommand{\\arraystretch}{1.15}")
    tbl.append("\\begin{tabular}{rrrr}")
    tbl.append("\\toprule")
    tbl.append("$S_{\\max}$ & \\#subsets & \\#unique ($M=1$) & unique fraction \\\\")
    tbl.append("\\midrule")
    for smax in sorted(counts_by_smax.keys()):
        n = int(counts_by_smax[smax])
        u = int(unique_by_smax.get(smax, 0))
        frac = (u / float(n)) if n else float("nan")
        tbl.append(f"{smax} & {n} & {u} & {frac:.4f} \\\\")
    tbl.append("\\bottomrule")
    tbl.append("\\end{tabular}")
    tbl.append("\\end{center}")

    # Additional compact table for the stop-fixed null.
    tbl.append("")
    tbl.append("\\begin{center}")
    tbl.append("\\small")
    tbl.append("\\setlength{\\tabcolsep}{6pt}")
    tbl.append("\\renewcommand{\\arraystretch}{1.15}")
    tbl.append("\\begin{tabular}{rr}")
    tbl.append("\\toprule")
    tbl.append("$S_{\\max}$ (stop-fixed) & \\#start choices (out of 61) \\\\")
    tbl.append("\\midrule")
    for smax in sorted(fixed_dist.keys()):
        tbl.append(f"{int(smax)} & {int(fixed_dist[smax])} \\\\")
    tbl.append("\\bottomrule")
    tbl.append("\\end{tabular}")
    tbl.append("\\end{center}")

    # If the unique-mu* hit list is short, record it explicitly as a final line.
    if fixed_unique_mu_star:
        tbl.append("")
        tbl.append(
            "Unique $\\mu^\\ast$ solutions under the stop-fixed null occur for start candidate(s): "
            + ", ".join(f"$\\mathrm{{{c}}}$" for c in fixed_unique_mu_star)
            + "."
        )
    write_text(generated_dir() / "control_objective_null_table.tex", "\n".join(tbl) + "\n")


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
        f"Under the uniform codon prior, the unique control-optimal solution "
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

    b = corr["reg_slope"]
    a = corr["reg_intercept"]
    r2 = corr["reg_r2"]
    p_b = corr["reg_p_slope"]
    se_b = corr["reg_se_slope"]

    # Single LaTeX paragraph fragment used inline.
    s = (
        f"OLS fit ($\\mathrm{{KD}}=a+b\\,N_{{\\max}}$): $b={b:.4f}\\pm {se_b:.4f}$ "
        f"($p={p_b:.4f}$), $a={a:.4f}$, $R^2={r2:.3f}$ (n={n}). "
        f"Correlation: Pearson $r={r:.3f}$ ($p={p:.4f}$), Spearman $\\rho={rho:.3f}$ ($p={p_rho:.4f}$)."
    )
    write_text(generated_dir() / "hydrophobicity_correlation.tex", s + "\n")


def generate_vmean_property_correlations(mu: dict[str, str]) -> None:
    """
    Exploratory correlations using V_mean (uniform-codon average of V per amino acid).
    """
    corr_h = vmean_hydrophobicity_correlation_under_mu(mu)
    corr_m = vmean_mass_correlation_under_mu(mu)

    def fmt(c: dict[str, float]) -> tuple[str, str, str, str, int, str, str, str, str, str]:
        n = int(c["n"])
        r = c["pearson_r"]
        p = c["pearson_p"]
        rho = c["spearman_rho"]
        p_rho = c["spearman_p"]
        b = c["reg_slope"]
        a = c["reg_intercept"]
        r2 = c["reg_r2"]
        p_b = c["reg_p_slope"]
        se_b = c["reg_se_slope"]
        return (
            f"{r:.3f}",
            f"{p:.4f}",
            f"{rho:.3f}",
            f"{p_rho:.4f}",
            n,
            f"{b:.4f}",
            f"{se_b:.4f}",
            f"{p_b:.4f}",
            f"{a:.4f}",
            f"{r2:.3f}",
        )

    r_h, p_h, rho_h, p_rho_h, n_h, b_h, sebh, pbh, a_h, r2_h = fmt(corr_h)
    r_m, p_m, rho_m, p_rho_m, n_m, b_m, sebm, pbm, a_m, r2_m = fmt(corr_m)
    assert n_h == n_m

    lines = []
    lines.append(
        f"For $V_\\mathrm{{mean}}$ (uniform-codon average of $V$ per amino acid), "
        f"OLS fits give: hydrophobicity $\\mathrm{{KD}}=a+b\\,V_\\mathrm{{mean}}$ with "
        f"$b={b_h}\\pm {sebh}$ ($p={pbh}$), $a={a_h}$, $R^2={r2_h}$; "
        f"mass $M=a+b\\,V_\\mathrm{{mean}}$ with $b={b_m}\\pm {sebm}$ ($p={pbm}$), $a={a_m}$, $R^2={r2_m}$ "
        f"(n={n_h}). Correlations: hydrophobicity Pearson $r={r_h}$ ($p={p_h}$), Spearman $\\rho={rho_h}$ ($p={p_rho_h}$); "
        f"mass Pearson $r={r_m}$ ($p={p_m}$), Spearman $\\rho={rho_m}$ ($p={p_rho_m}$)."
    )
    write_text(generated_dir() / "vmean_property_correlations.tex", "\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    print("=== Genetic code reverse compilation (Fold_6) ===")

    # ---- Cache short-circuit ----
    out_files = [
        "stop_fine_structure_rows.tex",
        "control_codons_rows.tex",
        "human_transcript_case_studies_rows.tex",
        "boundary_sector_codons_rows.tex",
        "amino_acid_spectrum_rows.tex",
        "codon_full_table_rows.tex",
        "control_objective_brief.tex",
        "control_objective_null_summary.tex",
        "control_objective_null_table.tex",
        "encoding_scan_summary.tex",
        "encoding_scan_table.tex",
        "mutual_information_summary.tex",
        "mutual_information_brief.tex",
        "fold6_invariants_summary.tex",
        "hydrophobicity_correlation.tex",
        "vmean_property_correlations.tex",
    ]
    out_paths = [generated_dir() / nm for nm in out_files]

    # Case-study inputs (optional, but they affect output rows).
    cases = [
        data_root() / "NM_000518.5.fasta",
        data_root() / "ENST00000381330.5.fasta",
    ]
    cache_file = data_root() / "_cache" / f"genetic_code_decompiler_v{int(ANALYSIS_VERSION)}.json"
    cache_key = {
        "analysis": "genetic_code_decompiler",
        "analysis_version": int(ANALYSIS_VERSION),
        "mu_star": MU_STAR,
        "inputs": [_fingerprint_file(p) for p in cases],
        "outputs": [str(p) for p in out_paths],
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and all(p.exists() for p in out_paths) and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {cache_file}")
        print("Wrote LaTeX fragments into:", generated_dir())
        return

    # 1) Control-boundary alignment optimum over K={AUG,UAA,UAG,UGA}.
    control_codons = ("AUG", "UAA", "UAG", "UGA")
    best_score = None
    best: list[dict[str, str]] = []
    hist = Counter()
    for mu in all_encodings():
        s = sum(1 for c in control_codons if fold_codon(c, mu).w in BOUNDARY_WORDS)
        hist[s] += 1
        if best_score is None or s > best_score:
            best_score = s
            best = [mu]
        elif s == best_score:
            best.append(mu)
    assert best_score is not None
    print("Control score S(mu) histogram over 24 encodings:", dict(hist))
    print("Max S(mu):", best_score, "encodings achieving max:", len(best))
    for mu in best:
        print("  best:", encoding_to_str(mu))

    if best != [MU_STAR]:
        raise AssertionError("Expected a unique mu* optimum under control-boundary alignment.")

    # 2) Emergent start/stop boundary homology (derived property).
    hits = [mu for mu in all_encodings() if satisfies_start_stop_boundary_homology(mu)]
    print("Start/stop boundary-homology encodings (derived):", len(hits))
    for mu in hits:
        print("  homology hit:", encoding_to_str(mu))

    # 3) Sanity checks for 14/48 symmetry
    aug = fold_codon("AUG", MU_STAR)
    uaa = fold_codon("UAA", MU_STAR)
    print("AUG:", aug)
    print("UAA:", uaa)
    if not (aug.n == 14 and uaa.n == 48 and aug.w == uaa.w == "100001"):
        raise AssertionError("14/48 symmetry check failed")

    # 4) Generate LaTeX fragments
    generate_stop_fine_structure(MU_STAR)
    generate_control_codons_table(MU_STAR)
    generate_human_transcript_case_studies(MU_STAR)
    generate_boundary_sector_codons(MU_STAR)
    generate_amino_acid_spectrum_rows(MU_STAR)
    generate_full_codon_table_rows(MU_STAR)
    generate_encoding_scan_summary()
    generate_encoding_scan_table()
    generate_control_objective_null_over_all_4codon_sets()
    generate_mutual_information_summary()
    generate_fold6_invariants_summary()
    generate_hydrophobicity_correlation(MU_STAR)
    generate_vmean_property_correlations(MU_STAR)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(cache_file, {"ok": True})
    write_json_atomic(cache_meta_path(cache_file), cache_meta)

    print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


