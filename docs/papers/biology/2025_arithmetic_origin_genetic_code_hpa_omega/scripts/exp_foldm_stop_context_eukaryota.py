# -*- coding: utf-8 -*-
"""
Multi-resolution (Fold_m) stop-context scan on eukaryotic RefSeq mRNA corpora.

Goal:
  Quantify how terminal-stop uplift-window contrasts depend on the Zeckendorf window length m.
  This complements the codon-level Fold_m resolution scan by adding a sequence-level check.

Datasets:
  - refseq_hsapiens_mrna (Human)
  - refseq_mmusculus_mrna (Mouse)
  - refseq_drerio_mrna (Zebrafish)

Method:
  - For each transcript, select the longest ORF across frames using AUG starts and UAA/UAG/UGA stops.
  - For each terminal stop class s in {UAA,UAG,UGA}, compute per-stop window means of uplift
    U_m(i)=Delta_m(c_i) in a k-codon window before and after the terminal stop (same frame).
  - Report fixed-effect meta-analysis across datasets for each (m,k,window,pair) using SE derived
    from per-dataset normal-approximation two-sample SE.

Outputs:
  - sections/generated/foldm_stop_context_meta_eukaryota.tex
  - sections/generated/foldm_stop_context_meta_eukaryota.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, START_CODON, STOP_CODONS, fold_codon_m, iter_fasta
from progress_tools import Heartbeat
from stats_tools import normal_two_sided_p


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_root() -> Path:
    return root_dir() / "data"


def read_manifest() -> dict[str, Any]:
    mp = data_root() / "manifest.json"
    return json.loads(mp.read_text(encoding="utf-8"))


def dataset_files_from_manifest(m: dict[str, Any], dataset_key: str) -> list[Path]:
    ds = (m.get("datasets") or {}).get(dataset_key)
    if not isinstance(ds, dict):
        raise SystemExit(f"Missing dataset in manifest: {dataset_key}")
    t = str(ds.get("type") or "")
    if t != "ncbi_refseq_dir":
        raise SystemExit(f"Unsupported dataset type for this script: {dataset_key} (type={t})")
    local_dir = root_dir() / str(ds["local_dir"])
    files = []
    for e in (ds.get("files", []) or []):
        if not isinstance(e, dict):
            continue
        name = e.get("name")
        if isinstance(name, str) and name:
            files.append(local_dir / name)
    if files:
        return files
    return sorted(local_dir.glob("*.gz"))


def _file_fingerprint(paths: list[Path]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for fp in paths:
        if not fp.exists():
            out.append({"name": fp.name, "missing": True})
            continue
        st = fp.stat()
        out.append(
            {
                "name": fp.name,
                "bytes": int(st.st_size),
                "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
            }
        )
    out.sort(key=lambda x: str(x.get("name") or ""))
    return out


@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    M2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        d2 = x - self.mean
        self.M2 += d * d2

    def sample_variance(self) -> float:
        if self.n <= 1:
            return 0.0
        return self.M2 / (self.n - 1)


@dataclass(frozen=True)
class BestOrf:
    frame: int
    start_base: int
    stop_base: int
    length_codons_including_stop: int


def best_orf_across_frames(seq: str) -> BestOrf | None:
    """
    Longest ORF across frames using AUG start and standard stops.
    Tie-breakers match exp_corpus_panel:
      - longer ORF wins
      - earlier start wins
      - lower frame wins
    """
    best: BestOrf | None = None
    for frame in (0, 1, 2):
        in_orf = False
        start_pos: int | None = None
        best_frame: BestOrf | None = None
        for pos in range(frame, len(seq) - 2, 3):
            codon = seq[pos : pos + 3]
            if codon not in GENETIC_CODE:
                in_orf = False
                start_pos = None
                continue
            if not in_orf:
                if codon == START_CODON:
                    in_orf = True
                    start_pos = pos
            else:
                if codon in STOP_CODONS:
                    if start_pos is not None:
                        length_codons = (pos - start_pos) // 3 + 1
                        cand = BestOrf(
                            frame=frame,
                            start_base=start_pos,
                            stop_base=pos,
                            length_codons_including_stop=length_codons,
                        )
                        if best_frame is None:
                            best_frame = cand
                        else:
                            key = (cand.length_codons_including_stop, -cand.start_base, -cand.frame)
                            key_best = (
                                best_frame.length_codons_including_stop,
                                -best_frame.start_base,
                                -best_frame.frame,
                            )
                            if key > key_best:
                                best_frame = cand
                    in_orf = False
                    start_pos = None
        if best_frame is None:
            continue
        if best is None:
            best = best_frame
            continue
        key = (best_frame.length_codons_including_stop, -best_frame.start_base, -best_frame.frame)
        key_best = (best.length_codons_including_stop, -best.start_base, -best.frame)
        if key > key_best:
            best = best_frame
    return best


def _is_num(x: object) -> bool:
    try:
        v = float(x)  # type: ignore[arg-type]
    except Exception:
        return False
    return (not math.isnan(v)) and math.isfinite(v)


def _fmt_float(x: object, *, nd: int = 4) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}"


def _fmt_z(x: object) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.2f}"


def _fmt_p(p: object) -> str:
    if not _is_num(p):
        return "-"
    p0 = float(p)
    if p0 == 0.0:
        return "<1e-300"
    if p0 < 1e-4:
        return f"{p0:.2e}"
    return f"{p0:.4f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m stop-context scan (eukaryota RefSeq mRNA)")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated Zeckendorf window lengths m to evaluate.")
    p.add_argument("--k-list", default="3,5,10,20", help="Comma-separated stop-context window radii k.")
    p.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat seconds (0 disables).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_stop_context_meta_eukaryota.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ms = []
    for p in str(args.m_list).split(","):
        p = p.strip()
        if not p:
            continue
        ms.append(int(p))
    ms = sorted({int(m) for m in ms if int(m) > 0})
    if not ms:
        raise SystemExit("--m-list must contain positive integers")

    ks = []
    for p in str(args.k_list).split(","):
        p = p.strip()
        if not p:
            continue
        ks.append(int(p))
    ks = sorted({int(k) for k in ks if int(k) > 0})
    if not ks:
        raise SystemExit("--k-list must contain positive integers")

    out_tex = Path(args.out_tex)
    mfest = read_manifest()
    ds_keys = [
        ("H_sapiens_mRNA_Prot", "refseq_hsapiens_mrna"),
        ("M_musculus_mRNA_Prot", "refseq_mmusculus_mrna"),
        ("D_rerio_mRNA_Prot", "refseq_drerio_mrna"),
    ]
    ds_files: dict[str, list[Path]] = {}
    for _label, key in ds_keys:
        files = dataset_files_from_manifest(mfest, key)
        missing = [fp for fp in files if not fp.exists()]
        if missing:
            raise SystemExit(f"Missing files for dataset {key}: {', '.join(str(p) for p in missing[:3])}")
        ds_files[key] = files

    cache_key = {
        "analysis": "foldm_stop_context_eukaryota",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "m_list": ms,
        "k_list": ks,
        "datasets": {
            key: _file_fingerprint(ds_files[key]) for (_lbl, key) in ds_keys
        },
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    # Precompute delta lookup for each m.
    delta_m: dict[int, dict[str, int]] = {}
    for m in ms:
        delta_m[int(m)] = {}
        for codon in GENETIC_CODE:
            delta_m[int(m)][codon] = int(fold_codon_m(codon, MU_STAR, m=int(m)).delta)

    # Per-dataset stats: dataset -> m -> stop -> k -> (before_stats, after_stats)
    stats: dict[str, dict[int, dict[str, dict[int, tuple[RunningStats, RunningStats]]]]] = {}

    hb_global = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] foldm_stop_context")
    hb_global.force(f"start ms={','.join(str(x) for x in ms)} ks={','.join(str(x) for x in ks)}")

    max_k = max(ks)
    for label, key in ds_keys:
        hb = Heartbeat(every_s=float(args.heartbeat_s), prefix=f"[progress] foldm_stop_context:{label}")
        hb.force(f"start files={len(ds_files[key])}")
        # init
        stats[key] = {}
        for m in ms:
            stats[key][int(m)] = {}
            for sc in STOP_CODONS:
                stats[key][int(m)][sc] = {}
                for k in ks:
                    stats[key][int(m)][sc][int(k)] = (RunningStats(), RunningStats())

        n_records = 0
        n_with_orf = 0
        for fp in ds_files[key]:
            for _rid, seq in iter_fasta(str(fp)):
                n_records += 1
                hb.maybe(f"file={fp.name} records={n_records} with_orf={n_with_orf}")
                best = best_orf_across_frames(seq)
                if best is None:
                    continue
                s = best.start_base
                t = best.stop_base
                stop_codon = seq[t : t + 3]
                start_codon = seq[s : s + 3]
                if start_codon != START_CODON:
                    continue
                if stop_codon not in STOP_CODONS:
                    continue
                n_with_orf += 1

                # Collect up to max_k codons before stop (inside ORF) and after stop (in transcript, same frame).
                before_codons: list[str] = []
                for pos in range(t - 3 * max_k, t, 3):
                    if pos < s:
                        continue
                    cod = seq[pos : pos + 3]
                    if cod not in GENETIC_CODE:
                        before_codons = []
                        break
                    before_codons.append(cod)
                # keep only last max_k (in case ORF shorter)
                if len(before_codons) > max_k:
                    before_codons = before_codons[-max_k:]

                after_codons: list[str] = []
                for pos in range(t + 3, t + 3 * max_k + 3, 3):
                    if pos + 3 > len(seq):
                        break
                    cod = seq[pos : pos + 3]
                    if cod not in GENETIC_CODE:
                        break
                    after_codons.append(cod)

                for m in ms:
                    b_d = [delta_m[int(m)][c] for c in before_codons]
                    a_d = [delta_m[int(m)][c] for c in after_codons]
                    for k in ks:
                        if len(b_d) >= int(k) and len(a_d) >= int(k):
                            before_mean = float(sum(b_d[-int(k) :])) / float(k)
                            after_mean = float(sum(a_d[: int(k)])) / float(k)
                            st_b, st_a = stats[key][int(m)][stop_codon][int(k)]
                            st_b.update(before_mean)
                            st_a.update(after_mean)

        hb.force(f"done records={n_records} with_orf={n_with_orf}")

    # Fixed-effect meta-analysis across the three eukaryotic corpora.
    # For each dataset we compute pairwise effects with SE from sample variances.
    pairs = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]
    rows: list[str] = []
    for m in ms:
        for side in ("after", "before"):
            for c1, c2 in pairs:
                pair_tex = f"{c1}$\\,$vs$\\,${c2}"
                for k in ks:
                    diffs: list[float] = []
                    ses: list[float] = []
                    for _label, key in ds_keys:
                        s1, s2 = stats[key][int(m)][c1][int(k)], stats[key][int(m)][c2][int(k)]
                        a1 = s1[1] if side == "after" else s1[0]
                        a2 = s2[1] if side == "after" else s2[0]
                        n1 = int(a1.n)
                        n2 = int(a2.n)
                        if n1 < 2 or n2 < 2:
                            continue
                        v1 = float(a1.sample_variance())
                        v2 = float(a2.sample_variance())
                        se2 = (v1 / float(n1)) + (v2 / float(n2))
                        if se2 <= 0:
                            continue
                        diff = float(a1.mean) - float(a2.mean)
                        diffs.append(diff)
                        ses.append(math.sqrt(se2))
                    if not diffs:
                        continue
                    wsum = 0.0
                    wdiff = 0.0
                    for d, se in zip(diffs, ses):
                        w = 1.0 / (se * se)
                        wsum += w
                        wdiff += w * d
                    if wsum <= 0:
                        continue
                    meta_diff = wdiff / wsum
                    meta_se = math.sqrt(1.0 / wsum)
                    z = meta_diff / meta_se if meta_se > 0 else float("nan")
                    p = normal_two_sided_p(float(z)) if meta_se > 0 else float("nan")
                    rows.append(
                        f"{int(m)} & {side} & {pair_tex} & {int(k)} & {len(diffs)} & {_fmt_float(meta_diff, nd=4)} & {_fmt_float(meta_se, nd=4)} & {_fmt_z(z)} & {_fmt_p(p)} \\\\"
                    )

    # LaTeX output
    lines: list[str] = []
    lines.append("Fixed-effect meta-analysis of terminal-stop uplift-window contrasts across eukaryotic RefSeq corpora (best ORF; Fold$_m$).")
    lines.append("")
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{rrlrlrrrr}")
    lines.append("\\toprule")
    lines.append("$m$ & window & pair & $k$ & $n$ & meta diff & meta se & $z$ & $p$ \\\\")
    lines.append("\\midrule")
    lines.extend(rows)
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    hb_global.force(f"wrote {out_tex}")


if __name__ == "__main__":
    main()


