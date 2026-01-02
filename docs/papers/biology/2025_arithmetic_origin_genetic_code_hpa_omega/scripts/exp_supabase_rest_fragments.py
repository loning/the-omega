# -*- coding: utf-8 -*-
"""
Generate LaTeX fragments from Supabase via PostgREST (HTTPS).

This is a practical alternative to direct Postgres connections (5432), which can be blocked
in some environments. The statistical products are still computed/stored inside Supabase
via SQL (tables/views), and this script only retrieves and formats them into LaTeX.

Required env vars (loaded from supabase.env by default):
  - SUPABASE_URL
  - SUPABASE_KEY
"""

from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from progress_tools import Heartbeat
from supabase_env import load_env_file


SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    return root_dir() / "sections" / "generated"


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: object | None = None,
    timeout_s: float = 60.0,
    ssl_context: ssl.SSLContext | None = None,
) -> tuple[int, dict[str, str], object | None]:
    data: bytes | None
    if body is None:
        data = None
    else:
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = dict(headers)
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            resp_headers = {k: v for k, v in resp.headers.items()}
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = int(getattr(e, "code", 0) or 0)
        resp_headers = {k: v for k, v in getattr(e, "headers", {}).items()}
        raw = e.read() if hasattr(e, "read") else b""
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling Supabase: {e}") from e

    if not raw:
        return status, resp_headers, None
    try:
        return status, resp_headers, json.loads(raw.decode("utf-8"))
    except Exception:
        return status, resp_headers, raw.decode("utf-8", errors="replace")


def _postgrest_base(url: str) -> str:
    return url.rstrip("/") + "/rest/v1"


def _headers_with_key(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _get_rows(
    *,
    supabase_url: str,
    supabase_key: str,
    relation: str,
    select: str,
    filters: dict[str, str] | None = None,
    order: str | None = None,
    limit: int | None = None,
    ssl_context: ssl.SSLContext | None = None,
) -> list[dict[str, Any]]:
    base = _postgrest_base(supabase_url)
    params: dict[str, str] = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit is not None and int(limit) > 0:
        params["limit"] = str(int(limit))
    qs = urllib.parse.urlencode(params)
    url = f"{base}/{urllib.parse.quote(relation)}?{qs}"
    headers = _headers_with_key(supabase_key)
    status, _, payload = _http_json(method="GET", url=url, headers=headers, body=None, ssl_context=ssl_context)
    if status not in (200, 206):
        raise RuntimeError(f"GET failed for {relation} (status={status}): {payload}")
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected payload type for {relation}: {type(payload)}")
    out: list[dict[str, Any]] = []
    for it in payload:
        if isinstance(it, dict):
            out.append(it)
    return out


def _tex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("~", "\\textasciitilde{}")
        .replace("^", "\\textasciicircum{}")
    )


def _pair_tex(pair: str) -> str:
    if "_vs_" in pair:
        a, b = pair.split("_vs_", 1)
        a = _tex_escape(a.strip())
        b = _tex_escape(b.strip())
        return f"{a}$\\,$vs$\\,${b}"
    return _tex_escape(pair)


def _fmt_float(x: Any, *, nd: int = 4) -> str:
    if x is None:
        return "-"
    try:
        v = float(x)
    except Exception:
        return _tex_escape(str(x))
    if v != v:  # NaN
        return "-"
    return f"{v:.{int(nd)}f}"


def _fmt_int(x: Any) -> str:
    if x is None:
        return "-"
    try:
        return str(int(x))
    except Exception:
        return _tex_escape(str(x))


def _fmt_p(x: Any) -> str:
    if x is None:
        return "-"
    try:
        v = float(x)
    except Exception:
        return _tex_escape(str(x))
    if v != v:  # NaN
        return "-"
    if v <= 0.0:
        return "<1e-300"
    if v < 1e-300:
        return "<1e-300"
    if v < 1e-3:
        return f"{v:.2e}"
    return f"{v:.4f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LaTeX fragments from Supabase via PostgREST.")
    p.add_argument(
        "--env-file",
        default="",
        help="Optional env file (key=value). If empty, will try supabase.env.",
    )
    p.add_argument("--force", action="store_true", help="Force re-query and rewrite outputs.")
    p.add_argument("--panel-name", default="corpus_panel_v1", help="panel name for corpus panel meta table.")
    p.add_argument("--panel-av", type=int, default=2, help="analysis_version for corpus panel meta table.")
    p.add_argument("--panel-k", type=int, default=10, help="k for corpus panel meta table.")
    p.add_argument("--recoding-dataset", default="ncbi_recoding_genbank", help="dataset for recoding multi-k table.")
    p.add_argument("--recoding-av", type=int, default=7, help="analysis_version for recoding multi-k table.")
    p.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval (seconds).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = root_dir()
    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] supabase_rest_fragments")

    env_file = Path(args.env_file) if str(args.env_file).strip() else (root / "supabase.env")
    if not env_file.exists():
        raise SystemExit(f"Missing env file: {env_file}")
    env = load_env_file(env_file)
    supabase_url = str(env.get("SUPABASE_URL") or "").strip()
    supabase_key = str(env.get("SUPABASE_KEY") or "").strip()
    if not supabase_url:
        raise SystemExit("Missing SUPABASE_URL in env.")
    if not supabase_key:
        raise SystemExit("Missing SUPABASE_KEY in env.")

    ssl_ctx = ssl.create_default_context()

    # ---- 1) Corpus-panel stop-context meta table (k=10) ----
    out_meta = generated_dir() / "corpus_panel_stop_context_meta_k10.tex"
    cache_key = {
        "analysis": "exp_supabase_rest_fragments",
        "version": int(SCRIPT_VERSION),
        "out": str(out_meta),
        "panel": str(args.panel_name),
        "panel_av": int(args.panel_av),
        "k": int(args.panel_k),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_meta, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_meta}")
    else:
        hb.force("fetching stop_context_meta_effects")
        rows = _get_rows(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            relation="stop_context_meta_effects",
            select="domain,window_side,k,pair,n_datasets,meta_diff,meta_se,z,p",
            filters={
                "panel": f"eq.{str(args.panel_name)}",
                "analysis_version": f"eq.{int(args.panel_av)}",
                "k": f"eq.{int(args.panel_k)}",
            },
            order="domain.asc,window_side.asc,pair.asc",
            ssl_context=ssl_ctx,
        )
        hb.force(f"formatting meta table (rows={len(rows)})")
        lines: list[str] = []
        lines.append("Fixed-effect meta-analysis of stop-context differences (by domain; $k=10$).")
        lines.append("")
        lines.append("\\begin{center}")
        lines.append("\\scriptsize")
        lines.append("\\setlength{\\tabcolsep}{4pt}")
        lines.append("\\renewcommand{\\arraystretch}{1.10}")
        lines.append("\\begin{tabular}{lllrrrrr}")
        lines.append("\\toprule")
        lines.append("domain & window & pair & $n$ & meta diff & meta se & $z$ & $p$ \\\\")
        lines.append("\\midrule")
        for r in rows:
            domain = _tex_escape(str(r.get("domain") or "-"))
            window_side = _tex_escape(str(r.get("window_side") or "-"))
            pair = _pair_tex(str(r.get("pair") or "-"))
            n = _fmt_int(r.get("n_datasets"))
            meta_diff = _fmt_float(r.get("meta_diff"), nd=4)
            meta_se = _fmt_float(r.get("meta_se"), nd=4)
            z = _fmt_float(r.get("z"), nd=3)
            p = _fmt_p(r.get("p"))
            lines.append(f"{domain} & {window_side} & {pair} & {n} & {meta_diff} & {meta_se} & {z} & {p} \\\\")
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\end{center}")
        lines.append("")
        write_text_atomic(out_meta, "\n".join(lines) + "\n")
        write_json_atomic(cache_meta_path(out_meta), cache_meta)
        print("Wrote:", out_meta, f"(rows={len(rows)})")

    # ---- 2) Recoding multi-k overall table ----
    out_rec = generated_dir() / "recoding_context_tests_multi_k.tex"
    cache_key = {
        "analysis": "exp_supabase_rest_fragments",
        "version": int(SCRIPT_VERSION),
        "out": str(out_rec),
        "recoding_dataset": str(args.recoding_dataset),
        "recoding_av": int(args.recoding_av),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_rec, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_rec}")
    else:
        hb.force("fetching recoding_context_effects_multi_k")
        rows = _get_rows(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            relation="recoding_context_effects_multi_k",
            select="label,window_side,k,diff,hedges_g,p_welch,q_welch",
            filters={
                "dataset": f"eq.{str(args.recoding_dataset)}",
                "analysis_version": f"eq.{int(args.recoding_av)}",
            },
            order="label.asc,window_side.asc,k.asc",
            ssl_context=ssl_ctx,
        )
        hb.force(f"formatting recoding multi-k table (rows={len(rows)})")
        lines = []
        lines.append("Multi-$k$ sensitivity for recoding context tests (overall comparisons).")
        lines.append("")
        lines.append("\\begin{center}")
        lines.append("\\scriptsize")
        lines.append("\\setlength{\\tabcolsep}{4pt}")
        lines.append("\\renewcommand{\\arraystretch}{1.10}")
        lines.append("\\begin{tabular}{>{\\raggedright\\arraybackslash}p{5.2cm}llrrrr}")
        lines.append("\\toprule")
        lines.append("comparison & window & $k$ & diff & $g$ & $p$ & $q$ \\\\")
        lines.append("\\midrule")
        for r in rows:
            label = _tex_escape(str(r.get("label") or "-"))
            window_side = _tex_escape(str(r.get("window_side") or "-"))
            k = _fmt_int(r.get("k"))
            diff = _fmt_float(r.get("diff"), nd=4)
            g = _fmt_float(r.get("hedges_g"), nd=3)
            p = _fmt_p(r.get("p_welch"))
            q = _fmt_p(r.get("q_welch"))
            lines.append(f"{label} & {window_side} & {k} & {diff} & {g} & {p} & {q} \\\\")
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\end{center}")
        lines.append("")
        write_text_atomic(out_rec, "\n".join(lines) + "\n")
        write_json_atomic(cache_meta_path(out_rec), cache_meta)
        print("Wrote:", out_rec, f"(rows={len(rows)})")

    hb.force("done")


if __name__ == "__main__":
    main()


