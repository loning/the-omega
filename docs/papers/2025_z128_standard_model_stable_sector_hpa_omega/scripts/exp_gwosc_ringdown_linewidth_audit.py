# -*- coding: utf-8 -*-
"""
Real-data falsification audit: GWOSC strain -> ringdown damping vs linewidth proxy.

Data source:
  - GWOSC EventAPI (GWTC-1-confident, GW150914, version v3)
  - We use the public "txt.gz" strain product (time [s], strain) for H1 and L1.

Audit goal (interface-level):
  - Extract a late-time ringdown segment after merger time t0 (GPS).
  - Fit a damped sinusoid envelope in the time domain to obtain tau_time and f_time.
  - Compute a frequency-domain linewidth proxy from the DFT peak width (FWHM) to obtain tau_fft.
  - Report mismatch between tau_time and tau_fft under explicit window/gate choices.

Notes:
  - Uses numpy for FFT/PSD utilities; deterministic and file-auditable.
  - If the cached data file is absent, the script writes a minimal note rows/summary and exits successfully.
  - This audit is \\AuditTag: it does not assert theorem-level statements.

Outputs (LaTeX fragments):
  - sections/generated/gwosc_ringdown_linewidth_rows.tex
  - sections/generated/gwosc_ringdown_linewidth_summary.tex
"""

from __future__ import annotations

import gzip
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import numpy as np

from common_paths import generated_dir, paper_root
from common_progress import ProgressEvery
from common_tex import write_lines


GWOSC_RELEASE_JSON = "https://gwosc.org/eventapi/json/GWTC-1-confident/"
GWOSC_EVENT_JSON = "https://gwosc.org/eventapi/json/GWTC-1-confident/GW150914/v3"
EVENT_KEY = "GW150914-v3"
# Fallback GPS time (seconds) for GW150914 merger (v3). Used if GWOSC API fetch fails.
GW150914_GPS_FALLBACK = 1126259462.4

EPS = 1e-12
EPS_SNR = 1e-300

def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"

def _fmt_sci(x: float, digits: int = 3) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}e}"

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _download(url: str, dst: Path) -> None:
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    with urllib.request.urlopen(url, timeout=60) as r:
        tmp.write_bytes(r.read())
    tmp.replace(dst)


def _load_json_url(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


@dataclass(frozen=True)
class StrainSeries:
    t: List[float]
    h: List[float]
    fs: float


@dataclass(frozen=True)
class TxtGzHeader:
    gps_start: Optional[float]
    fs: Optional[float]


def _parse_txt_gz_header(path: Path) -> TxtGzHeader:
    gps_start: Optional[float] = None
    fs_header: Optional[float] = None
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for _ in range(80):
            line = f.readline()
            if not line:
                break
            s = line.strip()
            if not s.startswith("#"):
                break
            if "samples per second" in s:
                for tok in s.replace("#", " ").split():
                    try:
                        v = float(tok)
                    except Exception:
                        continue
                    if v > 0:
                        fs_header = float(v)
                        break
            if "starting GPS" in s:
                toks = s.replace("#", " ").split()
                for i, tok in enumerate(toks):
                    if tok.lower() == "gps" and i + 1 < len(toks):
                        try:
                            gps_start = float(toks[i + 1])
                        except Exception:
                            gps_start = None
                        break
    return TxtGzHeader(gps_start=gps_start, fs=fs_header)


def _iter_txt_gz_strain(path: Path) -> Iterator[float]:
    """
    Yield strain samples from a GWOSC txt.gz product.
    Supports both 1-col (strain) and 2-col (time, strain) variants.
    """
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            if not parts:
                continue
            try:
                # 1-col: parts[0] is strain; 2-col: parts[1] is strain.
                v = float(parts[-1])
            except Exception:
                continue
            yield float(v)

def _read_txt_gz(path: Path, fs_hint: Optional[float] = None) -> StrainSeries:
    # GWOSC txt.gz products appear in two common variants:
    #  (A) two-column: time, strain
    #  (B) one-column: strain samples only (time reconstructed from header GPSstart + fs)
    t: List[float] = []
    h: List[float] = []
    gps_start: Optional[float] = None
    fs_header: Optional[float] = None
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                # Example header lines:
                #   # This file has 4096 samples per second
                #   # starting GPS 1126259447 duration 32
                if "samples per second" in s:
                    for tok in s.replace("#", " ").split():
                        try:
                            v = float(tok)
                        except Exception:
                            continue
                        if v > 0:
                            fs_header = float(v)
                            break
                if "starting GPS" in s:
                    toks = s.replace("#", " ").split()
                    for i, tok in enumerate(toks):
                        if tok.lower() == "gps" and i + 1 < len(toks):
                            try:
                                gps_start = float(toks[i + 1])
                            except Exception:
                                gps_start = None
                            break
                continue

            parts = s.split()
            # Variant (B): one-column strain.
            if len(parts) == 1:
                try:
                    hh = float(parts[0])
                except Exception:
                    continue
                h.append(hh)
                continue
            # Variant (A): time, strain.
            if len(parts) >= 2:
                try:
                    tt = float(parts[0])
                    hh = float(parts[1])
                except Exception:
                    continue
                t.append(tt)
                h.append(hh)

    if t:
        if len(t) < 2:
            raise ValueError("Too few samples in two-column strain txt.gz")
        dt = float(t[1] - t[0])
        fs = fs_hint if (fs_hint is not None and fs_hint > 0) else float(1.0 / dt)
        return StrainSeries(t=t, h=h, fs=fs)

    # Reconstruct time grid for one-column variant.
    if len(h) < 2:
        raise ValueError("Empty strain txt.gz")
    fs = fs_hint if (fs_hint is not None and fs_hint > 0) else fs_header
    if fs is None or fs <= 0:
        raise ValueError("Missing sampling rate in header and no fs_hint provided")
    if gps_start is None or not math.isfinite(gps_start):
        raise ValueError("Missing GPS start time in header for one-column txt.gz")
    dt = 1.0 / float(fs)
    t = [float(gps_start + dt * float(i)) for i in range(len(h))]
    return StrainSeries(t=t, h=h, fs=float(fs))


def _slice_window(series: StrainSeries, t_lo: float, t_hi: float) -> StrainSeries:
    if t_hi <= t_lo:
        raise ValueError("Invalid window")
    t0 = series.t[0]
    dt = 1.0 / float(series.fs)
    i0 = int(max(0, math.floor((t_lo - t0) / dt)))
    i1 = int(min(len(series.t), math.ceil((t_hi - t0) / dt)))
    if i1 - i0 < 16:
        raise ValueError("Window too short")
    return StrainSeries(t=series.t[i0:i1], h=series.h[i0:i1], fs=series.fs)


def _detrend_mean(h: List[float]) -> List[float]:
    m = sum(h) / float(len(h))
    return [float(x - m) for x in h]

def _hann(h: List[float]) -> List[float]:
    n = len(h)
    if n <= 1:
        return list(h)
    out: List[float] = []
    for i, x in enumerate(h):
        w = 0.5 * (1.0 - math.cos(2.0 * math.pi * float(i) / float(n - 1)))
        out.append(float(w * x))
    return out

def _median(xs: List[float]) -> float:
    ys = sorted(float(x) for x in xs if math.isfinite(float(x)))
    if not ys:
        return float("nan")
    n = len(ys)
    if n % 2 == 1:
        return float(ys[n // 2])
    return float(0.5 * (ys[n // 2 - 1] + ys[n // 2]))

def _fir_bandpass_kernel(fs: float, f_lo: float, f_hi: float, taps: int = 401) -> List[float]:
    """
    Windowed-sinc FIR bandpass: ideal LP(f_hi) - LP(f_lo), Hann window.
    Deterministic, standard-library only.
    """
    if taps % 2 == 0:
        taps += 1
    if not (fs > 0 and 0.0 < f_lo < f_hi < 0.5 * fs):
        raise ValueError("Invalid FIR bandpass parameters")
    m = (taps - 1) // 2
    out: List[float] = []
    for n in range(taps):
        k = n - m
        if k == 0:
            h = 2.0 * (f_hi - f_lo) / fs
        else:
            x_hi = 2.0 * math.pi * f_hi * float(k) / fs
            x_lo = 2.0 * math.pi * f_lo * float(k) / fs
            h = (math.sin(x_hi) - math.sin(x_lo)) / (math.pi * float(k))
        w = 0.5 * (1.0 - math.cos(2.0 * math.pi * float(n) / float(taps - 1)))
        out.append(float(h * w))
    # Normalize approximately by unit gain at center frequency.
    f0 = 0.5 * (f_lo + f_hi)
    re = 0.0
    im = 0.0
    for n, hn in enumerate(out):
        k = n - m
        ang = -2.0 * math.pi * f0 * float(k) / fs
        re += hn * math.cos(ang)
        im += hn * math.sin(ang)
    g = math.sqrt(re * re + im * im)
    if g > 0:
        out = [float(x / g) for x in out]
    return out

def _fir_apply(x: List[float], h: List[float]) -> List[float]:
    """
    Same-length convolution output centered to input (linear-phase FIR).
    """
    n = len(x)
    m = len(h)
    if n == 0 or m == 0:
        return []
    half = (m - 1) // 2
    y: List[float] = []
    for i in range(n):
        acc = 0.0
        for k in range(m):
            j = i + k - half
            if 0 <= j < n:
                acc += float(h[k]) * float(x[j])
        y.append(float(acc))
    return y


def _welch_psd_stream(
    path: Path,
    *,
    fs: float,
    nperseg: int,
    noverlap: int,
    fmin: float,
    fmax: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Streaming Welch PSD estimate using rFFT periodograms.
    The txt.gz products are huge; we avoid loading the full array into memory.
    """
    if not (fs > 0 and nperseg > 0 and 0 <= noverlap < nperseg):
        raise ValueError("Invalid Welch parameters")
    step = int(nperseg - noverlap)
    win = np.hanning(int(nperseg)).astype(np.float64)
    win_pow = float(np.sum(win * win))
    if win_pow <= 0:
        raise ValueError("Bad Welch window power")

    buf: List[float] = []
    acc: Optional[np.ndarray] = None
    n_seg = 0
    seg_idx = 0
    prog = ProgressEvery(label=f"gwosc welch {path.name}", total=None, interval_s=60.0)
    prog.start()

    for x in _iter_txt_gz_strain(path):
        buf.append(float(x))
        if len(buf) < nperseg:
            continue
        seg = np.array(buf[:nperseg], dtype=np.float64)
        seg = seg - float(np.mean(seg))
        seg = seg * win
        X = np.fft.rfft(seg)
        Pxx = (np.abs(X) ** 2) / (win_pow * float(fs))
        if acc is None:
            acc = np.array(Pxx, dtype=np.float64)
        else:
            acc += Pxx
        n_seg += 1
        # hop
        buf = buf[step:]
        seg_idx += 1
        prog.maybe(seg_idx)

    if acc is None or n_seg <= 0:
        raise ValueError("No segments accumulated for PSD")
    psd = acc / float(n_seg)
    freqs = np.fft.rfftfreq(int(nperseg), d=1.0 / float(fs))
    m = (freqs >= float(fmin)) & (freqs <= float(fmax))
    freqs_b = freqs[m]
    psd_b = psd[m]
    if freqs_b.size < 8:
        raise ValueError("Too few PSD bins in band")
    return freqs_b, psd_b


def _welch_psd_array(
    x: List[float],
    *,
    fs: float,
    nperseg: int,
    noverlap: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Welch PSD estimate on an in-memory window (pre-merger noise window).
    """
    if not (fs > 0 and nperseg > 0 and 0 <= noverlap < nperseg):
        raise ValueError("Invalid Welch parameters")
    step = int(nperseg - noverlap)
    if len(x) < nperseg:
        raise ValueError("Noise window too short for Welch")
    win = np.hanning(int(nperseg)).astype(np.float64)
    win_pow = float(np.sum(win * win))
    if win_pow <= 0:
        raise ValueError("Bad Welch window power")
    acc: Optional[np.ndarray] = None
    n_seg = 0
    i0 = 0
    while i0 + nperseg <= len(x):
        seg = np.array(x[i0 : i0 + nperseg], dtype=np.float64)
        seg = seg - float(np.mean(seg))
        seg = seg * win
        X = np.fft.rfft(seg)
        Pxx = (np.abs(X) ** 2) / (win_pow * float(fs))
        if acc is None:
            acc = np.array(Pxx, dtype=np.float64)
        else:
            acc += Pxx
        n_seg += 1
        i0 += step
    if acc is None or n_seg <= 0:
        raise ValueError("No Welch segments accumulated")
    psd = acc / float(n_seg)
    freqs = np.fft.rfftfreq(int(nperseg), d=1.0 / float(fs))
    return freqs, psd


def _whiten_via_psd(x: List[float], fs: float, psd_freqs: np.ndarray, psd_vals: np.ndarray) -> List[float]:
    """
    Frequency-domain whitening: X(f) -> X(f)/sqrt(PSD(f)).
    """
    n = len(x)
    if n < 16:
        return list(x)
    arr = np.array(x, dtype=np.float64)
    arr = arr - float(np.mean(arr))
    X = np.fft.rfft(arr)
    freqs = np.fft.rfftfreq(n, d=1.0 / float(fs))
    psd_clip = np.maximum(psd_vals, float(EPS))
    log_psd = np.log(psd_clip)
    log_psd_i = np.interp(freqs, psd_freqs, log_psd, left=float(log_psd[0]), right=float(log_psd[-1]))
    psd_i = np.exp(log_psd_i)
    W = X / np.sqrt(psd_i)
    y = np.fft.irfft(W, n=n)
    return [float(v) for v in y.tolist()]

def _cos_sin_fit(h: List[float], fs: float, f: float, tau: float) -> Tuple[float, float, float]:
    """
    Fit h(t) ~ exp(-t/tau) * [a cos(2pi f t) + b sin(2pi f t)] in least squares,
    returning (a, b, mse). Here t is assumed to start at 0 with step 1/fs.
    """
    if not (f > 0 and tau > 0):
        return (0.0, 0.0, float("inf"))
    w = 2.0 * math.pi * float(f)
    dt = 1.0 / float(fs)
    # Normal equations for 2-parameter linear regression.
    s_cc = s_ss = s_cs = 0.0
    s_ch = s_sh = 0.0
    s_hh = 0.0
    for i, hi in enumerate(h):
        t = float(i) * dt
        e = math.exp(-t / float(tau))
        c = e * math.cos(w * t)
        s = e * math.sin(w * t)
        s_cc += c * c
        s_ss += s * s
        s_cs += c * s
        s_ch += c * hi
        s_sh += s * hi
        s_hh += hi * hi
    det = s_cc * s_ss - s_cs * s_cs
    if abs(det) < 1e-24:
        return (0.0, 0.0, float("inf"))
    a = (s_ch * s_ss - s_sh * s_cs) / det
    b = (s_sh * s_cc - s_ch * s_cs) / det
    # MSE
    # residual sum = ||h||^2 - [a b] * [s_ch s_sh]^T (since design is linear in a,b)
    # More explicitly: RSS = hh - 2(a*s_ch + b*s_sh) + a^2*s_cc + 2ab*s_cs + b^2*s_ss
    rss = s_hh - 2.0 * (a * s_ch + b * s_sh) + (a * a) * s_cc + 2.0 * a * b * s_cs + (b * b) * s_ss
    mse = float(rss / float(len(h)))
    return (float(a), float(b), float(mse))


def _tau_from_log_rms_envelope(h: List[float], fs: float, *, bin_s: float = 0.01) -> Tuple[float, float]:
    """
    Envelope fallback: estimate tau by fitting log(RMS) vs time in short bins.
    Returns (tau_env, r2_env). If not identifiable, returns (nan, nan).
    """
    if not (fs > 0 and bin_s > 0):
        return (float("nan"), float("nan"))
    n = len(h)
    bin_n = int(max(8, round(float(bin_s) * float(fs))))
    if n < 4 * bin_n:
        return (float("nan"), float("nan"))
    xs: List[float] = []
    ys: List[float] = []
    eps = 1e-18
    i0 = 0
    t_step = 1.0 / float(fs)
    while i0 + bin_n <= n:
        seg = h[i0 : i0 + bin_n]
        # RMS
        s2 = 0.0
        for v in seg:
            s2 += float(v) * float(v)
        rms = math.sqrt(s2 / float(bin_n))
        t_mid = (float(i0) + 0.5 * float(bin_n)) * t_step
        xs.append(float(t_mid))
        ys.append(float(math.log(rms + eps)))
        i0 += bin_n
    if len(xs) < 6:
        return (float("nan"), float("nan"))
    # Linear regression y = a + b x
    xbar = sum(xs) / float(len(xs))
    ybar = sum(ys) / float(len(ys))
    s_xx = 0.0
    s_xy = 0.0
    for x, y in zip(xs, ys):
        dx = x - xbar
        dy = y - ybar
        s_xx += dx * dx
        s_xy += dx * dy
    if abs(s_xx) < 1e-24:
        return (float("nan"), float("nan"))
    b = s_xy / s_xx
    a = ybar - b * xbar
    # Need negative slope for decay.
    if not (math.isfinite(b) and b < -1e-9):
        return (float("nan"), float("nan"))
    tau = float(-1.0 / b)
    # R^2
    ss_tot = 0.0
    ss_res = 0.0
    for x, y in zip(xs, ys):
        yhat = a + b * x
        ss_tot += (y - ybar) * (y - ybar)
        ss_res += (y - yhat) * (y - yhat)
    r2 = 1.0 - (ss_res / max(ss_tot, 1e-24))
    return (float(tau), float(r2))


def _grid_fit_tau_f(h: List[float], fs: float, f_grid: List[float], tau_grid: List[float]) -> Tuple[float, float, float]:
    """
    Return (best_f, best_tau, best_mse) by a bounded deterministic grid search.
    """
    # Tie-break discipline (audit):
    #  - primary: minimize mse
    #  - secondary (within a small relative tolerance): prefer smaller tau to avoid "infinite tau" drift in noise
    best_mse = float("inf")
    best_f = float("nan")
    best_tau = float("nan")
    prog = ProgressEvery(label="gwosc_ringdown grid", total=len(f_grid) * len(tau_grid), interval_s=60.0)
    prog.start()
    k = 0
    for tau in tau_grid:
        for f in f_grid:
            _, _, mse = _cos_sin_fit(h, fs=fs, f=f, tau=tau)
            if not math.isfinite(mse):
                k += 1
                prog.maybe(k)
                continue
            if mse < best_mse:
                best_mse = float(mse)
                best_f = float(f)
                best_tau = float(tau)
            else:
                # If within rel_tol of current best mse, prefer smaller tau.
                rel_tol = 1e-3
                if best_mse > 0 and mse <= best_mse * (1.0 + rel_tol):
                    if float(tau) < float(best_tau):
                        best_f = float(f)
                        best_tau = float(tau)
            k += 1
            prog.maybe(k)
    return (float(best_f), float(best_tau), float(best_mse))


def _dft_mag2(h: List[float], fs: float, f_min: float, f_max: float, n_freq: int) -> Tuple[List[float], List[float]]:
    """
    Compute a band-limited DFT magnitude^2 on an explicit uniform frequency grid.
    O(N * n_freq) but N is kept small by windowing.
    """
    n = len(h)
    norm = float(max(1, n)) ** 2
    dt = 1.0 / float(fs)
    freqs: List[float] = []
    mags: List[float] = []
    for j in range(int(n_freq)):
        f = float(f_min) + (float(j) / float(max(1, n_freq - 1))) * float(f_max - f_min)
        w = 2.0 * math.pi * f
        re = 0.0
        im = 0.0
        for i, hi in enumerate(h):
            t = float(i) * dt
            ang = -w * t
            re += hi * math.cos(ang)
            im += hi * math.sin(ang)
        freqs.append(f)
        mags.append(float((re * re + im * im) / norm))
    return freqs, mags


def _fwhm_with_floor(
    freqs: List[float],
    mags_sig: List[float],
    mags_noise: List[float],
    *,
    snr_min: float = 5.0,
) -> Optional[Tuple[float, float, float, float]]:
    """
    Return (f0, f_lo, f_hi, df) using a noise-referenced half-maximum:
      half := noise(f0) + 0.5*(sig(f0)-noise(f0)).

    Gate:
      SNR proxy := (sig(f0)-noise(f0)) / max(noise(f0), EPS) must exceed snr_min.
    """
    if (
        not freqs
        or len(freqs) < 5
        or len(freqs) != len(mags_sig)
        or len(freqs) != len(mags_noise)
    ):
        return None
    # Peak on noise-subtracted power.
    def _score(j: int) -> float:
        return float(mags_sig[j] - mags_noise[j])

    j0 = max(range(len(freqs)), key=_score)
    s0 = float(mags_sig[j0])
    n0 = float(mags_noise[j0])
    if not (math.isfinite(s0) and math.isfinite(n0)):
        return None
    if s0 <= n0:
        return None
    snr = (s0 - n0) / max(float(n0), EPS_SNR)
    if not (snr > float(snr_min)):
        return None
    half = float(n0 + 0.5 * (s0 - n0))

    # Left crossing
    j = j0
    while j > 0 and mags_sig[j] > half:
        j -= 1
    if j == 0:
        return None
    f1, m1 = float(freqs[j]), float(mags_sig[j])
    f2, m2 = float(freqs[j + 1]), float(mags_sig[j + 1])
    if m2 == m1:
        return None
    f_lo = f1 + (half - m1) * (f2 - f1) / (m2 - m1)

    # Right crossing
    j = j0
    while j < len(mags_sig) - 1 and mags_sig[j] > half:
        j += 1
    if j == len(mags_sig) - 1:
        return None
    f1, m1 = float(freqs[j - 1]), float(mags_sig[j - 1])
    f2, m2 = float(freqs[j]), float(mags_sig[j])
    if m2 == m1:
        return None
    f_hi = f1 + (half - m1) * (f2 - f1) / (m2 - m1)

    df = float(max(0.0, f_hi - f_lo))
    return (float(freqs[j0]), float(f_lo), float(f_hi), float(df))


def _fwhm_with_floor_diag(
    freqs: List[float],
    mags_sig: List[float],
    mags_noise: List[float],
    *,
    snr_min: float = 5.0,
    peak_center_hz: Optional[float] = None,
    peak_half_window_hz: float = 25.0,
) -> Tuple[Optional[Tuple[float, float, float, float]], float, float, str]:
    """
    Like _fwhm_with_floor, but returns diagnostics:
      (pk_or_none, snr_proxy, noise_floor_at_peak, reason)
    where reason is one of:
      OK | BADINPUT | SNRNEG | SNRFAIL | FWHMLEFT | FWHMRIGHT | FWHMFLAT
    """
    if (
        not freqs
        or len(freqs) < 5
        or len(freqs) != len(mags_sig)
        or len(freqs) != len(mags_noise)
    ):
        return (None, float("nan"), float("nan"), "BADINPUT")

    def _score(j: int) -> float:
        return float(mags_sig[j] - mags_noise[j])

    # Peak selection:
    # - If a center frequency is given (from time-domain fit), restrict to a local neighborhood to avoid band-edge artifacts.
    # - Otherwise fall back to global peak on noise-subtracted power.
    if peak_center_hz is not None and math.isfinite(float(peak_center_hz)):
        c = float(peak_center_hz)
        lo = float(c - peak_half_window_hz)
        hi = float(c + peak_half_window_hz)
        idx = [j for j, f in enumerate(freqs) if (float(f) >= lo and float(f) <= hi)]
        if len(idx) >= 5:
            j0 = max(idx, key=_score)
        else:
            j0 = max(range(len(freqs)), key=_score)
    else:
        j0 = max(range(len(freqs)), key=_score)

    # Band-edge gate: if peak sits too close to boundary, FWHM crossings are ill-posed.
    if j0 <= 2 or j0 >= len(freqs) - 3:
        s0 = float(mags_sig[j0])
        n0 = float(mags_noise[j0])
        snr = (s0 - n0) / max(float(n0), EPS_SNR) if (math.isfinite(s0) and math.isfinite(n0)) else float("nan")
        return (None, float(snr), float(n0), "PEAKEDGE")
    s0 = float(mags_sig[j0])
    n0 = float(mags_noise[j0])
    if not (math.isfinite(s0) and math.isfinite(n0)):
        return (None, float("nan"), float("nan"), "BADINPUT")
    if s0 <= n0:
        snr = (s0 - n0) / max(float(n0), EPS_SNR)
        return (None, float(snr), float(n0), "SNRNEG")
    snr = (s0 - n0) / max(float(n0), EPS_SNR)
    if not (snr > float(snr_min)):
        return (None, float(snr), float(n0), "SNRFAIL")
    half = float(n0 + 0.5 * (s0 - n0))

    # Left crossing
    j = j0
    while j > 0 and mags_sig[j] > half:
        j -= 1
    if j == 0:
        return (None, float(snr), float(n0), "FWHMLEFT")
    f1, m1 = float(freqs[j]), float(mags_sig[j])
    f2, m2 = float(freqs[j + 1]), float(mags_sig[j + 1])
    if m2 == m1:
        return (None, float(snr), float(n0), "FWHMFLAT")
    f_lo = f1 + (half - m1) * (f2 - f1) / (m2 - m1)

    # Right crossing
    j = j0
    while j < len(mags_sig) - 1 and mags_sig[j] > half:
        j += 1
    if j == len(mags_sig) - 1:
        return (None, float(snr), float(n0), "FWHMRIGHT")
    f1, m1 = float(freqs[j - 1]), float(mags_sig[j - 1])
    f2, m2 = float(freqs[j]), float(mags_sig[j])
    if m2 == m1:
        return (None, float(snr), float(n0), "FWHMFLAT")
    f_hi = f1 + (half - m1) * (f2 - f1) / (m2 - m1)

    df = float(max(0.0, f_hi - f_lo))
    return ((float(freqs[j0]), float(f_lo), float(f_hi), float(df)), float(snr), float(n0), "OK")


def main() -> None:
    out = generated_dir()
    rows_path = out / "gwosc_ringdown_linewidth_rows.tex"
    sum_path = out / "gwosc_ringdown_linewidth_summary.tex"

    data_dir = paper_root() / "data" / "real_world" / "gwosc"
    _ensure_dir(data_dir)

    # Cache target: use the 32s, 4kHz, txt.gz product for H1 and L1.
    fn_h1 = "H-H1_GWOSC_4KHZ_R1-1126259447-32.txt.gz"
    fn_l1 = "L-L1_GWOSC_4KHZ_R1-1126259447-32.txt.gz"
    # Optional PSD cache: use the 4096s, 4kHz, txt.gz product for Welch whitening (better identifiability).
    fn_h1_long = "H-H1_GWOSC_4KHZ_R1-1126257415-4096.txt.gz"
    fn_l1_long = "L-L1_GWOSC_4KHZ_R1-1126257415-4096.txt.gz"
    p_h1 = data_dir / fn_h1
    p_l1 = data_dir / fn_l1
    p_h1_long = data_dir / fn_h1_long
    p_l1_long = data_dir / fn_l1_long

    # If data is absent, emit a minimal note and exit successfully.
    if not (p_h1.is_file() and p_l1.is_file()):
        write_lines(rows_path, [r"% (GWOSC ringdown audit: missing cached strain txt.gz files)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{GWOSC ringdown falsification audit (real data).} \AuditTag "
                + r"Cached GWOSC strain products were not found under \texttt{data/real\_world/gwosc/}. "
                + r"To activate this audit, download the public GW150914 H1/L1 32s 4kHz txt.gz strain files "
                + r"and rerun \texttt{scripts/exp\_gwosc\_ringdown\_linewidth\_audit.py}.",
            ],
        )
        return

    # Load event metadata for merger time (fallback to constant if network is unavailable).
    try:
        rel = _load_json_url(GWOSC_RELEASE_JSON)
        ev = rel.get("events", {}).get(EVENT_KEY, {})
        gps0 = float(ev.get("GPS", float("nan")))
    except Exception:
        gps0 = float("nan")
    if not math.isfinite(gps0):
        gps0 = float(GW150914_GPS_FALLBACK)

    # Read strain series
    s_h1 = _read_txt_gz(p_h1, fs_hint=4096.0)
    s_l1 = _read_txt_gz(p_l1, fs_hint=4096.0)

    # Gates: explicit bandpass and explicit window family.
    # GW150914 ringdown sits around a few hundred Hz; keep a conservative band away from very low-frequency drift.
    f_band_lo, f_band_hi = 180.0, 350.0
    bp = _fir_bandpass_kernel(fs=4096.0, f_lo=f_band_lo, f_hi=f_band_hi, taps=401)

    # PSD whitening gate:
    #  - Prefer long cached products only if they look complete enough.
    #  - Otherwise, estimate Welch PSD from the in-file pre-merger noise window (robust & deterministic).
    def _looks_like_complete_long_file(p: Path) -> bool:
        try:
            return p.is_file() and p.stat().st_size > 50_000_000
        except Exception:
            return False

    use_long_psd = _looks_like_complete_long_file(p_h1_long) and _looks_like_complete_long_file(p_l1_long)
    welch_cfg = dict(nperseg=16384, noverlap=8192, fmin=f_band_lo, fmax=f_band_hi)  # 4s segments @ 4kHz
    welch_noise_cfg = dict(nperseg=8192, noverlap=4096)  # 2s segments on the local noise window

    # Noise window (fallback / local floor): an early pre-merger segment inside the same 32s snippet.
    noise_lo = float(s_h1.t[0] + 1.0)
    noise_hi = float(gps0 - 5.0)
    if noise_hi <= noise_lo:
        noise_lo = float(s_h1.t[0] + 1.0)
        noise_hi = float(s_h1.t[0] + 10.0)

    # Ringdown window family (post-merger), declared explicitly.
    # The point is to test stability under bounded window choices.
    win_family = [
        (0.03, 0.10),
        (0.04, 0.11),
        (0.05, 0.12),
        # Longer windows improve frequency resolution for FWHM; kept as additional audit cases.
        (0.03, 0.18),
        (0.04, 0.22),
        (0.05, 0.25),
    ]

    rows: List[str] = []
    summary_lines: List[str] = []
    mismatch_all: List[float] = []
    reason_all: dict[str, int] = {}
    tau_bound_all = 0

    for det, series in [("H1", s_h1), ("L1", s_l1)]:
        # Noise baseline spectrum (same band/grid as ringdown), after applying the same filter/whitening gates.
        noise = _slice_window(series, t_lo=noise_lo, t_hi=noise_hi)
        noise_filt = _fir_apply(_detrend_mean(noise.h), bp)
        whiten_mode = "NONE"
        # PSD for whitening: long file if complete, else Welch on local noise window.
        if use_long_psd:
            long_path = p_h1_long if det == "H1" else p_l1_long
            hdr = _parse_txt_gz_header(long_path)
            fs_long = float(hdr.fs) if (hdr.fs is not None and hdr.fs > 0) else 4096.0
            psd_f, psd_v = _welch_psd_stream(long_path, fs=fs_long, **welch_cfg)
            whiten_mode = "WELCH_LONG"
        else:
            f_all, p_all = _welch_psd_array(noise_filt, fs=noise.fs, **welch_noise_cfg)
            m = (f_all >= float(f_band_lo)) & (f_all <= float(f_band_hi))
            psd_f, psd_v = f_all[m], p_all[m]
            whiten_mode = "WELCH_LOCAL"

        # Apply whitening consistently to the noise baseline.
        noise_filt = _whiten_via_psd(noise_filt, fs=noise.fs, psd_freqs=psd_f, psd_vals=psd_v)
        noise_filt = _hann(noise_filt)
        freqs_ref, mags_noise = _dft_mag2(noise_filt, fs=noise.fs, f_min=f_band_lo, f_max=f_band_hi, n_freq=801)
        noise_floor = float(_median(mags_noise))
        noise_flat = [noise_floor for _ in mags_noise]

        det_mismatches: List[float] = []
        det_reasons: dict[str, int] = {}
        det_tau_bound = 0
        for w_id, (dt_lo, dt_hi) in enumerate(win_family, start=1):
            t_lo = gps0 + float(dt_lo)
            t_hi = gps0 + float(dt_hi)
            win = _slice_window(series, t_lo=t_lo, t_hi=t_hi)
            h0 = _fir_apply(_detrend_mean(win.h), bp)
            # Apply the same whitening PSD to ringdown.
            h0 = _whiten_via_psd(h0, fs=win.fs, psd_freqs=psd_f, psd_vals=psd_v)
            h = _hann(h0)

            freqs0, mags0 = _dft_mag2(h, fs=win.fs, f_min=f_band_lo, f_max=f_band_hi, n_freq=801)
            # Align grids (should match by construction).
            mags_sig = mags0

            # Peak localization on a noise-floor-subtracted spectrum (robust constant floor).
            jpk = max(range(len(mags_sig)), key=lambda j: float(mags_sig[j] - noise_floor))
            f_peak = float(freqs0[jpk])

            # Fit grid near peak.
            f_lo = max(f_band_lo, f_peak - 40.0)
            f_hi = min(f_band_hi, f_peak + 40.0)
            f_grid = [f_lo + 1.0 * float(k) for k in range(int(max(1, round((f_hi - f_lo) / 1.0))) + 1)]
            # Bounded tau grid (audit choice): keep finite upper bound to avoid runaway "no damping" fits in noise.
            tau_grid = [0.002 + 0.0005 * float(k) for k in range(0, 97)]  # 2ms .. 50ms
            best_f, best_tau, best_mse = _grid_fit_tau_f(h, fs=win.fs, f_grid=f_grid, tau_grid=tau_grid)
            tau_max = float(max(tau_grid))
            tau_bound_hit = 1 if (math.isfinite(best_tau) and abs(float(best_tau) - tau_max) <= 1e-15) else 0
            det_tau_bound += int(tau_bound_hit)
            tau_bound_all += int(tau_bound_hit)

            # Time-domain fit quality gate (R^2 proxy on variance).
            mu = sum(h) / float(len(h))
            var = sum((x - mu) * (x - mu) for x in h) / float(len(h))
            r2 = 1.0 - (best_mse / max(var, EPS)) if (math.isfinite(best_mse) and math.isfinite(var)) else float("nan")
            tau_env, r2_env = _tau_from_log_rms_envelope(h, fs=win.fs, bin_s=0.010)

            # Use time-fit center only if it is not itself pinned to the band edge.
            peak_center = best_f
            edge_margin_hz = 15.0
            if not (math.isfinite(peak_center) and (f_band_lo + edge_margin_hz) <= peak_center <= (f_band_hi - edge_margin_hz)):
                peak_center = None
            pk, snr_proxy, n0_peak, reason = _fwhm_with_floor_diag(
                freqs0,
                mags_sig,
                noise_flat,
                snr_min=2.0,
                peak_center_hz=peak_center,
                peak_half_window_hz=25.0,
            )
            fwhm_pass = 1 if pk is not None else 0
            det_reasons[reason] = det_reasons.get(reason, 0) + 1
            reason_all[reason] = reason_all.get(reason, 0) + 1
            if pk is None:
                f0 = float("nan")
                df = float("nan")
                tau_fft = float("nan")
                abslog = float("nan")
                tau_method = "NA"
                reason_out = reason
            else:
                f0, _, _, df = pk
                tau_fft = float(1.0 / (math.pi * df)) if (df > 0.0) else float("nan")
                # If tau hits the grid upper bound, fall back to an envelope estimate.
                if tau_bound_hit == 1 and math.isfinite(tau_env) and tau_env > 0:
                    # Envelope must pass a minimal quality gate; otherwise treat tau as non-identifiable.
                    if math.isfinite(r2_env) and float(r2_env) >= 0.20 and float(tau_env) <= 2.0:
                        tau_used = float(tau_env)
                        tau_method = "ENV"
                    else:
                        tau_used = float("nan")
                        tau_method = "ENVFAIL"
                else:
                    tau_used = float(best_tau)
                    tau_method = "GRID"
                abslog = (
                    float(abs(math.log((tau_used + EPS) / (tau_fft + EPS))))
                    if (tau_used > 0 and tau_fft > 0 and math.isfinite(tau_used) and math.isfinite(tau_fft))
                    else float("nan")
                )
            if not math.isfinite(abslog):
                reason_out = reason + "+TAUFAIL"
            elif tau_bound_hit == 1 and tau_method == "ENV":
                reason_out = reason + "+ENV"
            elif tau_bound_hit == 1:
                reason_out = reason + "+TAUBOUND"
            else:
                reason_out = reason

            if math.isfinite(abslog):
                det_mismatches.append(float(abslog))
                mismatch_all.append(float(abslog))

            rows.append(
                " & ".join(
                    [
                        det,
                        str(int(w_id)),
                        _fmt(gps0, 3),
                        _fmt(dt_lo, 3),
                        _fmt(dt_hi, 3),
                        str(len(h)),
                        _fmt(f_peak, 3),
                        _fmt(best_f, 3),
                        _fmt(best_tau, 6),
                        _fmt(tau_env, 6),
                        _fmt(f0, 3),
                        _fmt(df, 6),
                        _fmt(tau_fft, 6),
                        _fmt(abslog, 6),
                        _fmt(r2, 6),
                        _fmt(r2_env, 6),
                        _fmt_sci(snr_proxy, 3),
                        _fmt_sci(n0_peak, 3),
                        str(int(fwhm_pass)),
                        reason_out,
                        whiten_mode,
                        str(int(tau_bound_hit)),
                        tau_method,
                    ]
                )
                + r" \\"
            )

        if det_mismatches:
            summary_lines.append(
                rf"{det}: abslog mismatch range [{_fmt(min(det_mismatches),6)}, {_fmt(max(det_mismatches),6)}], "
                rf"median {_fmt(_median(det_mismatches),6)} over {len(det_mismatches)} windows. "
                + "reasons: "
                + ", ".join(f"{k}={det_reasons[k]}" for k in sorted(det_reasons.keys()))
                + f"; tauBoundHit={det_tau_bound}"
            )
        else:
            summary_lines.append(
                rf"{det}: no valid windows passed the FWHM SNR gate. "
                + "reasons: "
                + ", ".join(f"{k}={det_reasons[k]}" for k in sorted(det_reasons.keys()))
                + f"; tauBoundHit={det_tau_bound}"
            )

    write_lines(rows_path, rows if rows else ["% (no rows)"])
    write_lines(
        sum_path,
        [
            r"\paragraph{GWOSC ringdown falsification audit (real data).} \AuditTag "
            + r"We test a time-domain vs frequency-domain consistency gate on the public GW150914 strain snippets (H1/L1, 4 kHz, 32 s product). "
            + r"Gates: a deterministic FIR bandpass (180--350 Hz); Welch-PSD whitening (local pre-merger noise window, or long cached products when complete); "
            + r"an in-file pre-merger noise window to estimate the band noise floor; and a bounded post-merger window family. "
            + r"For each window we fit a damped sinusoid on the filtered (and optionally whitened) strain to obtain $(f_{\mathrm{time}},\tau_{\mathrm{time}})$ and compute a noise-referenced FWHM $\Delta f$ in the same band, inducing $\tau_{\mathrm{fft}}\approx 1/(\pi\,\Delta f)$. "
            + r"We report the abs-log mismatch $|\log(\tau_{\mathrm{time}}/\tau_{\mathrm{fft}})|$ per detector under the declared gates.",
            r"\paragraph{Detector summaries.} \AuditTag " + " ".join(summary_lines),
            (
                r"\paragraph{Aggregate.} \AuditTag "
                + (
                    rf"Median abslog mismatch across all valid rows: {_fmt(_median(mismatch_all),6)}. "
                    + "reasons: "
                    + ", ".join(f"{k}={reason_all[k]}" for k in sorted(reason_all.keys()))
                    + f"; tauBoundHit={tau_bound_all}"
                    if mismatch_all
                    else ("No valid rows. " + "reasons: " + ", ".join(f"{k}={reason_all[k]}" for k in sorted(reason_all.keys())) + f"; tauBoundHit={tau_bound_all}")
                )
            ),
        ],
    )

    print("Wrote sections/generated/gwosc_ringdown_linewidth_rows.tex")
    print("Wrote sections/generated/gwosc_ringdown_linewidth_summary.tex")


if __name__ == "__main__":
    main()

