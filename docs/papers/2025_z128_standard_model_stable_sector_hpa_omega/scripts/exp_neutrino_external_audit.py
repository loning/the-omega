# -*- coding: utf-8 -*-
"""
External neutrino audit ledger generator (Match/Audit only).

Reads:
  - data/neutrino_external_audit/inputs.json

Writes:
  - sections/generated/neutrino_external_audit_rows.tex
  - sections/generated/neutrino_external_audit_summary.tex
  - sections/generated/neutrino_external_audit_internal_rows.tex

This script intentionally does NOT perform any CAP selection. It merely records
external constraints and emits deterministic pass/fail placeholders suitable
for inclusion in Appendix~52.

Only the Python standard library is used.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from common_tex import write_lines


# Representative oscillation splittings (eV^2), kept consistent with exp_neutrino_mass_interface.py.
DM21 = 7.42e-5
DM31_NO = 2.517e-3
DM31_IO = 2.498e-3  # absolute value for inverted ordering


@dataclass(frozen=True)
class Channel:
    id: str
    name: str
    observable: str
    bound_type: str
    value: Optional[float]
    value_range: Optional[List[float]]
    references: List[str]
    comment: str


def load_inputs(path: Path) -> List[Channel]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if int(data.get("schema_version", 0)) != 1:
        raise ValueError("Unsupported schema_version in neutrino external audit inputs.")
    chs = data.get("channels", [])
    out: List[Channel] = []
    for ch in chs:
        out.append(
            Channel(
                id=str(ch.get("id", "")),
                name=str(ch.get("name", "")),
                observable=str(ch.get("observable", "")),
                bound_type=str(ch.get("bound_type", "")),
                value=ch.get("value", None),
                value_range=ch.get("value_range", None),
                references=list(ch.get("references", [])),
                comment=str(ch.get("comment", "")),
            )
        )
    if not out:
        raise ValueError("No channels found in neutrino external audit inputs.")
    return out


def fmt_bound(ch: Channel) -> str:
    # Deterministic, minimal formatting. If missing, show 'pending'.
    unit = ""
    if ch.observable in {"m_beta", "sigma_mnu", "m_beta_beta"}:
        unit = r"\,\mathrm{eV}"
    if ch.value_range is not None and len(ch.value_range) == 2:
        lo, hi = ch.value_range
        return f"$[{lo},\\,{hi}]{unit}$"
    if ch.value is None:
        return r"\textit{pending input}"
    return f"${ch.value}{unit}$"


def fmt_refs(ch: Channel) -> str:
    if not ch.references:
        return ""
    keys = ",".join(ch.references)
    return rf"~\cite{{{keys}}}"


def fmt_role() -> str:
    return r"\MatchTag audit-only"


def fmt_status(ch: Channel) -> str:
    # External constraints are audit-only; if missing value we mark pending.
    if ch.value is None and ch.value_range is None:
        return r"\textit{pending}"
    return r"\textit{recorded}"


def _parse_pmns_s12_s13_pred(pmns_angles_rows: Path) -> tuple[float, float]:
    """
    Parse predicted s12 and s13 from sections/generated/pmns_angles_rows.tex.

    Expected row format (LaTeX fragment):
      $s_{12}$ & <pred> & <ref> & <mismatch> \\
      ...
      $s_{13}$ & <pred> & <ref> & <mismatch> \\
    """
    lines = pmns_angles_rows.read_text(encoding="utf-8").splitlines()
    s12 = None
    s13 = None
    for line in lines:
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 2:
            continue
        key = cols[0]
        val = cols[1]
        try:
            x = float(val)
        except Exception:
            continue
        if "s_{12}" in key:
            s12 = x
        if "s_{13}" in key:
            s13 = x
    if s12 is None or s13 is None:
        raise AssertionError("Failed to parse s12/s13 from pmns_angles_rows.tex")
    return float(s12), float(s13)


def _min_mass_spectra_eV() -> dict[str, dict[str, float]]:
    """
    Minimal-mass (m_lightest=0) spectra in eV inferred from oscillation splittings.

    Keep consistent with scripts/exp_neutrino_mass_interface.py.
    """
    return {
        "NO": {"m1": 0.0, "m2": math.sqrt(DM21), "m3": math.sqrt(DM31_NO)},
        "IO": {"m1": math.sqrt(DM31_IO), "m2": math.sqrt(DM31_IO + DM21), "m3": 0.0},
    }


def _spectrum_from_mlightest(ordering: str, m0: float) -> dict[str, float]:
    if m0 < 0.0:
        raise ValueError("m0 must be nonnegative.")
    if ordering == "NO":
        m1 = m0
        m2 = math.sqrt(m0 * m0 + DM21)
        m3 = math.sqrt(m0 * m0 + DM31_NO)
        return {"m1": float(m1), "m2": float(m2), "m3": float(m3)}
    if ordering == "IO":
        m3 = m0
        m1 = math.sqrt(m0 * m0 + DM31_IO)
        m2 = math.sqrt(m0 * m0 + DM31_IO + DM21)
        return {"m1": float(m1), "m2": float(m2), "m3": float(m3)}
    raise ValueError("ordering must be 'NO' or 'IO'.")


def _solve_mlightest_max_from_sigma(ordering: str, sigma_bound: float) -> float | None:
    """
    Solve for the maximal lightest mass m0 (eV) such that Sigma(m0) <= sigma_bound.
    If sigma_bound is below the minimal-mass sum, return None (ordering excluded).
    """
    if sigma_bound <= 0.0:
        return None
    m_min = _spectrum_from_mlightest(ordering, m0=0.0)
    sig_min = _sigma_mnu(m_min)
    if sig_min > sigma_bound:
        return None
    lo = 0.0
    hi = float(sigma_bound)
    # Ensure hi is above the bound (it will be for realistic bounds).
    for _ in range(60):
        if _sigma_mnu(_spectrum_from_mlightest(ordering, m0=hi)) >= sigma_bound:
            break
        hi *= 2.0
    # Bisection.
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        sig_mid = _sigma_mnu(_spectrum_from_mlightest(ordering, m0=mid))
        if sig_mid <= sigma_bound:
            lo = mid
        else:
            hi = mid
    return float(lo)


def _sigma_mnu(m: dict[str, float]) -> float:
    return float(m["m1"] + m["m2"] + m["m3"])


def _m_beta(m: dict[str, float], ue2: tuple[float, float, float]) -> float:
    u1, u2, u3 = ue2
    x = u1 * (m["m1"] ** 2) + u2 * (m["m2"] ** 2) + u3 * (m["m3"] ** 2)
    return math.sqrt(max(0.0, x))


def _m_bb_bounds(m: dict[str, float], ue2: tuple[float, float, float]) -> tuple[float, float]:
    # Phase-agnostic bounds (polygon inequalities) with a_i = |U_ei|^2 m_i.
    u1, u2, u3 = ue2
    a1 = u1 * m["m1"]
    a2 = u2 * m["m2"]
    a3 = u3 * m["m3"]
    mx = a1 + a2 + a3
    mn = max(0.0, a1 - a2 - a3, a2 - a1 - a3, a3 - a1 - a2)
    return float(mn), float(mx)


def _interval_status(min_val: float, max_val: float, upper_bound: float) -> str:
    """
    Classify an interval [min_val, max_val] against an upper bound:
      - EXCLUDED: min_val > B (entire interval above the bound)
      - OK:       max_val <= B (entire interval below the bound)
      - PARTIAL:  otherwise
    """
    if min_val > upper_bound:
        return "EXCLUDED"
    if max_val <= upper_bound:
        return "OK"
    return "PARTIAL"


def _fmt_ev(x: float, sig: int = 6) -> str:
    # Compact deterministic formatting for small eV-scale numbers.
    return f"{x:.{sig}g}"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    inp = root / "data" / "neutrino_external_audit" / "inputs.json"
    channels = load_inputs(inp)

    rows: List[str] = []
    recorded = 0
    pending = 0
    for ch in channels:
        b = fmt_bound(ch)
        refs = fmt_refs(ch)
        role = fmt_role()
        status = fmt_status(ch)
        if "pending" in status:
            pending += 1
        else:
            recorded += 1
        # 4-column table: channel | observable/bound | role | status
        rows.append(f"{ch.name} & {ch.observable}: {b}{refs} & {role} & {status} \\\\")

    rows.append(r"\bottomrule")

    # Internal prediction summary (uses only already-closed PMNS moduli + the minimal mass-scale interface).
    pmns_angles = root / "sections" / "generated" / "pmns_angles_rows.tex"
    if pmns_angles.is_file():
        s12, s13 = _parse_pmns_s12_s13_pred(pmns_angles)
        c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
        c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
        # |U_e1|^2, |U_e2|^2, |U_e3|^2 in PDG parameterization (Majorana phases do not enter).
        ue1_2 = (c12 * c13) ** 2
        ue2_2 = (s12 * c13) ** 2
        ue3_2 = (s13) ** 2
        ue2 = (float(ue1_2), float(ue2_2), float(ue3_2))

        spectra = _min_mass_spectra_eV()
        no = spectra["NO"]
        io = spectra["IO"]
        sig_no = _sigma_mnu(no)
        sig_io = _sigma_mnu(io)
        mb_no = _m_beta(no, ue2=ue2)
        mb_io = _m_beta(io, ue2=ue2)
        mbb_no = _m_bb_bounds(no, ue2=ue2)
        mbb_io = _m_bb_bounds(io, ue2=ue2)

        internal_lines = [
            r"\textbf{Internal neutrino audit numbers (interface; no external inputs).}",
            rf"Using the closed PMNS moduli and the minimal-mass interface spectra ($m_\mathrm{{lightest}}=0$):",
            rf"NO: $\Sigma m_\nu={_fmt_ev(sig_no)}\,\mathrm{{eV}}$, $m_\beta={_fmt_ev(mb_no)}\,\mathrm{{eV}}$, "
            rf"$m_{{\beta\beta}}\in[{_fmt_ev(mbb_no[0])},\,{_fmt_ev(mbb_no[1])}]\,\mathrm{{eV}}$ (phase-agnostic).",
            rf"IO: $\Sigma m_\nu={_fmt_ev(sig_io)}\,\mathrm{{eV}}$, $m_\beta={_fmt_ev(mb_io)}\,\mathrm{{eV}}$, "
            rf"$m_{{\beta\beta}}\in[{_fmt_ev(mbb_io[0])},\,{_fmt_ev(mbb_io[1])}]\,\mathrm{{eV}}$ (phase-agnostic).",
        ]

        # Internal table rows (auditable interface summary).
        internal_table_rows: List[str] = []
        internal_table_rows.append(
            rf"NO & \texttt{{min}} & {_fmt_ev(0.0)} & {_fmt_ev(sig_no)} & {_fmt_ev(mb_no)} & {_fmt_ev(mbb_no[0])} & {_fmt_ev(mbb_no[1])} \\"
        )
        internal_table_rows.append(
            rf"IO & \texttt{{min}} & {_fmt_ev(0.0)} & {_fmt_ev(sig_io)} & {_fmt_ev(mb_io)} & {_fmt_ev(mbb_io[0])} & {_fmt_ev(mbb_io[1])} \\"
        )

        # External bound compatibility (audit-only): if a bound is present, check whether it already excludes
        # the minimal-mass spectra. (If not excluded at m_lightest=0, the ordering remains compatible.)
        by_obs: Dict[str, Channel] = {c.observable: c for c in channels}
        compat_lines: List[str] = []
        c_sig = by_obs.get("sigma_mnu")
        if c_sig is not None and c_sig.value is not None:
            B = float(c_sig.value)
            no_excl = sig_no > B
            io_excl = sig_io > B
            compat_lines.append(
                rf"Cosmology audit (upper bound): $\Sigma m_\nu < {_fmt_ev(B)}\,\mathrm{{eV}}$"
                rf"{fmt_refs(c_sig)}. Minimal-mass check: NO {_fmt_ev(sig_no)} ({'EXCLUDED' if no_excl else 'OK'}), "
                rf"IO {_fmt_ev(sig_io)} ({'EXCLUDED' if io_excl else 'OK'})."
            )
            # Invert the bound to obtain an audit-only cap on the lightest mass.
            m0_no = _solve_mlightest_max_from_sigma("NO", sigma_bound=B)
            m0_io = _solve_mlightest_max_from_sigma("IO", sigma_bound=B)
            if m0_no is not None:
                spec = _spectrum_from_mlightest("NO", m0=m0_no)
                mb = _m_beta(spec, ue2=ue2)
                mbb = _m_bb_bounds(spec, ue2=ue2)
                sig = _sigma_mnu(spec)
                internal_table_rows.append(
                    rf"NO & \texttt{{sigma}} & {_fmt_ev(m0_no)} & {_fmt_ev(sig)} & {_fmt_ev(mb)} & {_fmt_ev(mbb[0])} & {_fmt_ev(mbb[1])} \\"
                )
                compat_lines.append(
                    rf"Cosmology inversion (audit-only): under $\Sigma m_\nu < {_fmt_ev(B)}\,\mathrm{{eV}}$"
                    rf"{fmt_refs(c_sig)}, NO implies $m_1\le {_fmt_ev(m0_no)}\,\mathrm{{eV}}$ and yields "
                    rf"$m_\beta\le {_fmt_ev(mb)}\,\mathrm{{eV}}$, $m_{{\beta\beta}}\in[{_fmt_ev(mbb[0])},{_fmt_ev(mbb[1])}]\,\mathrm{{eV}}$."
                )
            if m0_io is not None:
                spec = _spectrum_from_mlightest("IO", m0=m0_io)
                mb = _m_beta(spec, ue2=ue2)
                mbb = _m_bb_bounds(spec, ue2=ue2)
                sig = _sigma_mnu(spec)
                internal_table_rows.append(
                    rf"IO & \texttt{{sigma}} & {_fmt_ev(m0_io)} & {_fmt_ev(sig)} & {_fmt_ev(mb)} & {_fmt_ev(mbb[0])} & {_fmt_ev(mbb[1])} \\"
                )
                compat_lines.append(
                    rf"Cosmology inversion (audit-only): under $\Sigma m_\nu < {_fmt_ev(B)}\,\mathrm{{eV}}$"
                    rf"{fmt_refs(c_sig)}, IO implies $m_3\le {_fmt_ev(m0_io)}\,\mathrm{{eV}}$ and yields "
                    rf"$m_\beta\le {_fmt_ev(mb)}\,\mathrm{{eV}}$, $m_{{\beta\beta}}\in[{_fmt_ev(mbb[0])},{_fmt_ev(mbb[1])}]\,\mathrm{{eV}}$."
                )
        c_mb = by_obs.get("m_beta")
        if c_mb is not None and c_mb.value is not None:
            B = float(c_mb.value)
            no_excl = mb_no > B
            io_excl = mb_io > B
            compat_lines.append(
                rf"Beta-decay audit (upper bound): $m_\beta < {_fmt_ev(B)}\,\mathrm{{eV}}$"
                rf"{fmt_refs(c_mb)}. Minimal-mass check: NO {_fmt_ev(mb_no)} ({'EXCLUDED' if no_excl else 'OK'}), "
                rf"IO {_fmt_ev(mb_io)} ({'EXCLUDED' if io_excl else 'OK'})."
            )
        c_mbb = by_obs.get("m_beta_beta")
        if c_mbb is not None and c_mbb.value is not None:
            B = float(c_mbb.value)
            no_status = _interval_status(mbb_no[0], mbb_no[1], upper_bound=B)
            io_status = _interval_status(mbb_io[0], mbb_io[1], upper_bound=B)
            compat_lines.append(
                rf"0$\nu\beta\beta$ audit (upper bound): $m_{{\beta\beta}} < {_fmt_ev(B)}\,\mathrm{{eV}}$"
                rf"{fmt_refs(c_mbb)}. Phase-agnostic minimal-mass ranges: "
                rf"NO $[{_fmt_ev(mbb_no[0])},{_fmt_ev(mbb_no[1])}]$ ({no_status}), "
                rf"IO $[{_fmt_ev(mbb_io[0])},{_fmt_ev(mbb_io[1])}]$ ({io_status})."
            )
        c_neff = by_obs.get("delta_N_eff")
        if c_neff is not None and c_neff.value is not None:
            B = float(c_neff.value)
            # Minimal discrete proxy family: {0,1,3} (decoupled; one thermalized; three thermalized).
            v0 = 0.0
            v1 = 1.0
            v3 = 3.0
            s0 = "OK" if v0 <= B else "EXCLUDED"
            s1 = "OK" if v1 <= B else "EXCLUDED"
            s3 = "OK" if v3 <= B else "EXCLUDED"
            compat_lines.append(
                rf"Extra-radiation audit (upper bound): $|\Delta N_\mathrm{{eff}}| < {_fmt_ev(B)}$"
                rf"{fmt_refs(c_neff)}. Proxy family $\Delta N_\mathrm{{eff}}\in\{{0,1,3\}}$: "
                rf"$0$ ({s0}), $1$ ({s1}), $3$ ({s3})."
            )
            # Cold/partial-thermalization proxy: DeltaNeff ≈ n_R * xi^4, so xi ≤ (B/n_R)^{1/4}.
            if B > 0.0:
                xi1 = (B / 1.0) ** 0.25
                xi3 = (B / 3.0) ** 0.25
                compat_lines.append(
                    rf"Extra-radiation inversion (audit-only): if $\Delta N_\mathrm{{eff}}\approx n_R\xi^4$ (Appendix~\ref{{app:neutrino_external_audit_channels}}), "
                    rf"then $\xi\le(B/n_R)^{{1/4}}$ gives $\xi\le {_fmt_ev(xi1, sig=4)}$ for $n_R=1$ and $\xi\le {_fmt_ev(xi3, sig=4)}$ for $n_R=3$."
                )
        if compat_lines:
            internal_lines.extend([r"\textbf{External bound compatibility (audit-only).}", *compat_lines])
    else:
        internal_lines = [
            r"\textbf{Internal neutrino audit numbers.} \textit{pending} (missing \path{sections/generated/pmns_angles_rows.tex}).",
        ]
        internal_table_rows = [
            r"\multicolumn{7}{l}{\textit{pending (missing pmns\_angles\_rows.tex)}} \\",
        ]

    summary_lines = [
        rf"\textbf{{External-neutrino audit ledger.}} Recorded: {recorded}; pending: {pending}.",
        r"\textit{Note:} External inputs here are Match/Audit only and do not enter CAP selection.",
        *internal_lines,
    ]

    out_dir = root / "sections" / "generated"
    write_lines(out_dir / "neutrino_external_audit_rows.tex", rows)
    write_lines(out_dir / "neutrino_external_audit_summary.tex", summary_lines)
    write_lines(out_dir / "neutrino_external_audit_internal_rows.tex", list(internal_table_rows) + [r"\bottomrule"])
    print("Wrote sections/generated/neutrino_external_audit_rows.tex")
    print("Wrote sections/generated/neutrino_external_audit_summary.tex")
    print("Wrote sections/generated/neutrino_external_audit_internal_rows.tex")


if __name__ == "__main__":
    main()

