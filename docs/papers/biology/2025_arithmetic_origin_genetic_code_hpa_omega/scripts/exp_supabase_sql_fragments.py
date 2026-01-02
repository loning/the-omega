#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate LaTeX fragments by running SQL directly on Supabase Postgres.

Design goals:
  - SQL is written directly in this Python script (reproducibility).
  - Results are cached per fragment via cache sidecar meta JSON.
  - Uses Supabase Postgres (not sqlite).

Requirements:
  - pg8000 (install via requirements.txt in a venv)
  - DATABASE_URL in env or supabase.env (see supabase.env.template)
"""

from __future__ import annotations

import argparse
import hashlib
import os
import ssl
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from supabase_env import load_env_file


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_database_url(url: str) -> dict[str, Any]:
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("postgres", "postgresql"):
        raise SystemExit(f"Unsupported scheme in DATABASE_URL: {u.scheme!r}")
    if not u.hostname:
        raise SystemExit("DATABASE_URL missing hostname")
    db = (u.path or "").lstrip("/")
    if not db:
        raise SystemExit("DATABASE_URL missing database name in path")
    user = urllib.parse.unquote(u.username or "")
    password = urllib.parse.unquote(u.password or "")
    if not user:
        raise SystemExit("DATABASE_URL missing username")
    port = int(u.port or 5432)
    qs = urllib.parse.parse_qs(u.query or "")
    sslmode = (qs.get("sslmode", ["require"])[0] or "require").lower()
    return {
        "user": user,
        "password": password,
        "host": u.hostname,
        "port": port,
        "database": db,
        "sslmode": sslmode,
    }


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


def _to_tex_cell(x: Any) -> str:
    if x is None:
        return "-"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return str(x)
    s = str(x)
    if ("/" in s) or ("\\" in s):
        return f"\\path{{{_tex_escape(s)}}}"
    return _tex_escape(s)


def _rows_to_tex(rows: list[tuple[Any, ...]], *, bottomrule: bool = True) -> str:
    out = []
    for r in rows:
        out.append(" & ".join(_to_tex_cell(v) for v in r) + " \\\\")
    if bottomrule:
        out.append("\\bottomrule")
    return "\n".join(out) + "\n"


def _import_pg8000():
    try:
        import pg8000.dbapi  # type: ignore
    except Exception as e:
        raise SystemExit(
            "Missing dependency 'pg8000'. Install it in your venv with:\n"
            "  python3 -m pip install -r requirements.txt\n"
        ) from e
    return pg8000.dbapi


def _query_scalar(conn: Any, sql: str, params: tuple[Any, ...]) -> Any:
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            return None
        return row[0]
    finally:
        cur.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LaTeX fragments from Supabase SQL queries.")
    p.add_argument("--database-url", default="", help="Postgres connection URL. Defaults to DATABASE_URL.")
    p.add_argument(
        "--env-file",
        default="",
        help="Optional env file (key=value). If empty, will try supabase.env when present.",
    )
    p.add_argument("--force", action="store_true", help="Force re-query even if cached outputs exist.")
    p.add_argument("--recoding-av", type=int, default=7, help="analysis_version for public.recoding_sites.")
    p.add_argument("--recoding-k", type=int, default=10, help="k for public.recoding_sites.")
    p.add_argument(
        "--recoding-dataset",
        default="ncbi_recoding_genbank",
        help="dataset for public.recoding_context_effects_multi_k.",
    )
    p.add_argument("--panel-av", type=int, default=2, help="analysis_version for public.corpus_panel_items.")
    p.add_argument("--panel-name", default="corpus_panel_v1", help="panel name for public.corpus_panel_items.")
    p.add_argument("--ns-av", type=int, default=1, help="analysis_version for public.nonstandard_sequence_tests_items.")
    p.add_argument("--ns-panel", default="nonstandard_examples_v1", help="panel for public.nonstandard_sequence_tests_items.")
    p.add_argument("--refseq-dataset", default="human_refseq_mrna", help="dataset for public.refseq_stop_context_comp_results.")
    p.add_argument("--refseq-av", type=int, default=4, help="analysis_version for public.refseq_stop_context_comp_results.")
    p.add_argument("--refseq-k", type=int, default=10, help="k for public.refseq_stop_context_comp_results.")
    p.add_argument("--refseq-cand-set", default="reporter_v1", help="candidate_set for public.refseq_stop_context_candidates.")
    p.add_argument("--refseq-cand-set-coding", default="reporter_coding_v1", help="candidate_set for protein-coding RefSeq candidates.")
    p.add_argument("--enrich-av", type=int, default=1, help="analysis_version for public.boundary_enrichment_results.")
    p.add_argument("--nsc-dataset", default="ncbi_gc_prt", help="dataset for public.analysis_runs (nonstandard codes).")
    p.add_argument("--nsc-av", type=int, default=2, help="analysis_version for public.analysis_runs (nonstandard codes).")
    return p.parse_args()


@dataclass(frozen=True)
class QuerySpec:
    name: str
    out_tex: Path
    sql: str


def main() -> None:
    args = parse_args()
    cwd = root_dir()

    env_file = Path(args.env_file) if str(args.env_file).strip() else (cwd / "supabase.env")
    if env_file.exists():
        for k, v in load_env_file(env_file).items():
            os.environ.setdefault(k, v)

    db_url = str(args.database_url).strip() or (os.environ.get("DATABASE_URL") or "").strip()
    if not db_url:
        raise SystemExit("Missing DATABASE_URL (set env var, put it in supabase.env, or pass --database-url).")

    info = _parse_database_url(db_url)
    db_public = {
        "host": info.get("host"),
        "port": info.get("port"),
        "database": info.get("database"),
        "user": info.get("user"),
        "sslmode": info.get("sslmode"),
    }

    rec_av = int(args.recoding_av)
    rec_k = int(args.recoding_k)
    rec_dataset = str(args.recoding_dataset)
    rec_dataset_sql = rec_dataset.replace("'", "''")
    panel_av = int(args.panel_av)
    ns_av = int(args.ns_av)
    ref_av = int(args.refseq_av)
    ref_k = int(args.refseq_k)
    ref_cand_set = str(args.refseq_cand_set)
    ref_cand_set_coding = str(args.refseq_cand_set_coding)
    enrich_av = int(args.enrich_av)
    nsc_av = int(args.nsc_av)
    nsc_dataset = str(args.nsc_dataset)

    queries: list[QuerySpec] = [
        QuerySpec(
            name="sql_recoding_plus4_by_aa_domain_rows",
            out_tex=generated_dir() / "sql_recoding_plus4_by_aa_domain_rows.tex",
            sql=f"""
select
  aa,
  domain,
  count(*) as n,
  sum((plus4_nt='A')::int) as n_A,
  sum((plus4_nt='C')::int) as n_C,
  sum((plus4_nt='G')::int) as n_G,
  sum((plus4_nt='U')::int) as n_U
from public.recoding_sites
where analysis_version = {rec_av} and k = {rec_k}
group by 1,2
order by n desc, aa, domain;
""".strip(),
        ),
        QuerySpec(
            name="sql_recoding_top_after_nt6_rows",
            out_tex=generated_dir() / "sql_recoding_top_after_nt6_rows.tex",
            sql=f"""
with ranked as (
  select
    aa,
    after_nt6,
    count(*) as n,
    row_number() over (partition by aa order by count(*) desc, after_nt6 asc) as rn
  from public.recoding_sites
  where analysis_version = {rec_av} and k = {rec_k} and after_nt6 is not null and after_nt6 <> ''
  group by 1,2
)
select aa, after_nt6, n
from ranked
where rn <= 10
order by aa, rn;
""".strip(),
        ),
        QuerySpec(
            name="sql_recoding_candidate_context_rows",
            out_tex=generated_dir() / "sql_recoding_candidate_context_rows.tex",
            sql=f"""
select
  aa,
  codon_rna,
  domain,
  gene,
  version,
  pos_start,
  before_seq_dna,
  codon_dna,
  after_seq_dna,
  before_mean_delta,
  after_mean_delta,
  (after_mean_delta - before_mean_delta) as diff
from public.recoding_sites
where analysis_version = {rec_av} and k = {rec_k}
  and before_seq_dna is not null and after_seq_dna is not null
order by diff desc nulls last
limit 50;
""".strip(),
        ),
        QuerySpec(
            name="sql_recoding_multi_k_overall_compact_rows",
            out_tex=generated_dir() / "sql_recoding_multi_k_overall_compact_rows.tex",
            sql=f"""
select
  label,
  window_side,
  k,
  diff,
  hedges_g,
  p_welch,
  q_welch
from public.recoding_context_effects_multi_k
where dataset = '{rec_dataset_sql}'
  and analysis_version = {rec_av}
order by label, window_side, k;
""".strip(),
        ),
        QuerySpec(
            name="sql_panel_boundary_rates_rows",
            out_tex=generated_dir() / "sql_panel_boundary_rates_rows.tex",
            sql=f"""
select domain, label, code_id, mode, coding_tokens, boundary_rate
from public.corpus_panel_items
where panel = '{str(args.panel_name)}' and analysis_version = {panel_av} and present is true
order by domain, boundary_rate desc;
""".strip(),
        ),
        QuerySpec(
            name="sql_nonstandard_seqtests_rank_rows",
            out_tex=generated_dir() / "sql_nonstandard_seqtests_rank_rows.tex",
            sql=f"""
select
  label,
  code_id,
  records_used,
  start_boundary_rate,
  start_boundary_z,
  stop_boundary_rate,
  stop_boundary_z
from public.nonstandard_sequence_tests_items
where panel = '{str(args.ns_panel)}' and analysis_version = {ns_av} and present is true
order by abs(stop_boundary_z) desc nulls last;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_comp_results_rows",
            out_tex=generated_dir() / "sql_refseq_comp_results_rows.tex",
            sql=f"""
select method, scheme, window_side, pair, diff, p, bins_used, n
from public.refseq_stop_context_comp_results
where dataset = '{str(args.refseq_dataset)}' and analysis_version = {ref_av} and k = {ref_k}
order by method, scheme, window_side, pair;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_stop_context_candidates_rows",
            out_tex=generated_dir() / "sql_refseq_stop_context_candidates_rows.tex",
            sql=f"""
select
  stop_codon,
  group_label,
  rank,
  record_id,
  (stop_base + 1) as stop_pos_1based,
  before_seq_dna,
  stop_codon_dna,
  after_seq_dna,
  before_mean_delta,
  after_mean_delta,
  diff,
  plus4_nt,
  after_nt6
from public.refseq_stop_context_candidates
where dataset = '{str(args.refseq_dataset)}'
  and analysis_version = {ref_av}
  and candidate_set = '{ref_cand_set}'
  and k = {ref_k}
order by stop_codon, group_label, rank;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_stop_context_candidates_coding_rows",
            out_tex=generated_dir() / "sql_refseq_stop_context_candidates_coding_rows.tex",
            sql=f"""
select
  stop_codon,
  group_label,
  rank,
  record_id,
  (stop_base + 1) as stop_pos_1based,
  before_seq_dna,
  stop_codon_dna,
  after_seq_dna,
  before_mean_delta,
  after_mean_delta,
  diff,
  plus4_nt,
  after_nt6
from public.refseq_stop_context_candidates
where dataset = '{str(args.refseq_dataset)}'
  and analysis_version = {ref_av}
  and candidate_set = '{ref_cand_set_coding}'
  and k = {ref_k}
order by stop_codon, group_label, rank;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_stop_context_candidates_prefix_rows",
            out_tex=generated_dir() / "sql_refseq_stop_context_candidates_prefix_rows.tex",
            sql=f"""
with x as (
  select
    stop_codon,
    group_label,
    split_part(record_id, '_', 1) as prefix,
    count(*) as n
  from public.refseq_stop_context_candidates
  where dataset = '{str(args.refseq_dataset)}'
    and analysis_version = {ref_av}
    and candidate_set = '{ref_cand_set}'
    and k = {ref_k}
  group by 1,2,3
)
select stop_codon, group_label, prefix, n
from x
order by stop_codon, group_label, n desc, prefix asc;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_stop_context_candidates_coding_prefix_rows",
            out_tex=generated_dir() / "sql_refseq_stop_context_candidates_coding_prefix_rows.tex",
            sql=f"""
with x as (
  select
    stop_codon,
    group_label,
    split_part(record_id, '_', 1) as prefix,
    count(*) as n
  from public.refseq_stop_context_candidates
  where dataset = '{str(args.refseq_dataset)}'
    and analysis_version = {ref_av}
    and candidate_set = '{ref_cand_set_coding}'
    and k = {ref_k}
  group by 1,2,3
)
select stop_codon, group_label, prefix, n
from x
order by stop_codon, group_label, n desc, prefix asc;
""".strip(),
        ),
        QuerySpec(
            name="sql_boundary_enrichment_rank_rows",
            out_tex=generated_dir() / "sql_boundary_enrichment_rank_rows.tex",
            sql=f"""
select
  dataset,
  label,
  n_subset,
  boundary_rate_subset,
  boundary_rate_total,
  enrichment,
  p,
  q
from public.boundary_enrichment_results
where analysis_version = {enrich_av}
order by p asc nulls last
limit 50;
""".strip(),
        ),
        QuerySpec(
            name="sql_nonstandard_stop_migration_rows",
            out_tex=generated_dir() / "sql_nonstandard_stop_migration_rows.tex",
            sql=f"""
with run as (
  select payload
  from public.analysis_runs
  where dataset = '{str(nsc_dataset).replace("'", "''")}'
    and analysis = 'nonstandard_codes'
    and analysis_version = {nsc_av}
  order by inserted_at desc
  limit 1
),
items as (
  select jsonb_array_elements(run.payload->'items') as it
  from run
)
select
  (it->>'code_id')::int as code_id,
  jsonb_array_length(it->'stops') as n_stop,
  coalesce(array_to_string(array(select jsonb_array_elements_text(it->'stops') order by 1), ', '), '-') as stops,
  coalesce(array_to_string(array(select jsonb_array_elements_text(it->'stops_added') order by 1), ', '), '-') as added_vs_1,
  coalesce(array_to_string(array(select jsonb_array_elements_text(it->'stops_removed') order by 1), ', '), '-') as removed_vs_1,
  case
    when jsonb_typeof(it->'stop_boundary') = 'array' and jsonb_array_length(it->'stop_boundary') > 0
      then (it->'stop_boundary'->0->>'codon') || '(' || (it->'stop_boundary'->0->>'w') || ')'
    else '-'
  end as stop_in_boundary,
  ('pos' || (it->'best_sym_stop'->>'pos') || '/map' || (it->'best_sym_stop'->>'base')) as best_symmetry,
  (it->'best_sym_stop'->>'overlap')::int as overlap,
  (it->'best_sym_stop'->>'jaccard')::double precision as jaccard
from items
order by code_id;
""".strip(),
        ),
        QuerySpec(
            name="sql_panel_stop_context_effects_k10_rows",
            out_tex=generated_dir() / "sql_panel_stop_context_effects_k10_rows.tex",
            sql=f"""
select
  p.domain,
  p.label,
  p.mode,
  p.code_id,
  e.window_side,
  e.pair,
  e.n1,
  e.n2,
  e.diff,
  e.ci_low,
  e.ci_high,
  e.hedges_g,
  e.p,
  e.q
from public.stop_context_pairwise_effects e
join public.corpus_panel_items p
  on p.panel = e.panel
  and p.analysis_version = e.analysis_version
  and p.dataset = e.dataset
where e.panel = '{str(args.panel_name)}'
  and e.analysis_version = {panel_av}
  and e.k = 10
  and p.present is true
order by p.domain, p.label, e.window_side, e.pair;
""".strip(),
        ),
        QuerySpec(
            name="sql_panel_stop_context_meta_k10_rows",
            out_tex=generated_dir() / "sql_panel_stop_context_meta_k10_rows.tex",
            sql=f"""
with base as (
  select
    p.domain,
    e.window_side,
    e.pair,
    e.diff,
    e.ci_low,
    e.ci_high
  from public.stop_context_pairwise_effects e
  join public.corpus_panel_items p
    on p.panel = e.panel
    and p.analysis_version = e.analysis_version
    and p.dataset = e.dataset
  where e.panel = '{str(args.panel_name)}'
    and e.analysis_version = {panel_av}
    and e.k = 10
    and p.present is true
    and e.diff is not null
    and e.ci_low is not null
    and e.ci_high is not null
),
w as (
  select
    domain,
    window_side,
    pair,
    diff,
    ((ci_high - ci_low) / (2.0 * 1.96)) as se,
    1.0 / power(((ci_high - ci_low) / (2.0 * 1.96)), 2) as weight
  from base
  where (ci_high - ci_low) > 0
),
agg as (
  select
    domain,
    window_side,
    pair,
    sum(weight * diff) / sum(weight) as meta_diff,
    sqrt(1.0 / sum(weight)) as meta_se
  from w
  group by 1,2,3
),
z as (
  select
    domain,
    window_side,
    pair,
    meta_diff,
    meta_se,
    (meta_diff / meta_se) as z
  from agg
  where meta_se > 0
)
select
  domain,
  window_side,
  pair,
  meta_diff,
  meta_se,
  z,
  2.0 * (1.0 - 0.5 * (1.0 + erf(abs(z) / sqrt(2.0)))) as p
from z
order by window_side, pair, domain;
""".strip(),
        ),
        QuerySpec(
            name="sql_panel_codon_usage_null_rows",
            out_tex=generated_dir() / "sql_panel_codon_usage_null_rows.tex",
            sql=f"""
select
  p.domain,
  p.label,
  p.mode,
  n.total_codons,
  n.obs_zbar,
  n.null_mean_zbar,
  n.z_zbar,
  n.p_zbar,
  n.obs_ubar,
  n.null_mean_ubar,
  n.z_ubar,
  n.p_ubar
from public.dataset_codon_usage_null n
join public.corpus_panel_items p
  on p.panel = n.panel
  and p.analysis_version = n.analysis_version
  and p.dataset = n.dataset
where n.panel = '{str(args.panel_name)}'
  and n.analysis_version = {panel_av}
  and p.present is true
order by p.domain, p.label;
""".strip(),
        ),
        QuerySpec(
            name="sql_panel_start_context_k10_rows",
            out_tex=generated_dir() / "sql_panel_start_context_k10_rows.tex",
            sql=f"""
select
  p.domain,
  p.label,
  p.mode,
  s.start_event,
  s.k,
  s.n_before,
  s.before_mean,
  s.n_after,
  s.after_mean
from public.start_context_means s
join public.corpus_panel_items p
  on p.panel = s.panel
  and p.analysis_version = s.analysis_version
  and p.dataset = s.dataset
where s.panel = '{str(args.panel_name)}'
  and s.analysis_version = {panel_av}
  and s.k = 10
  and p.present is true
order by p.domain, p.label, s.start_event;
""".strip(),
        ),
        QuerySpec(
            name="sql_assay_readthrough_constructs_with_measurements_rows",
            out_tex=generated_dir() / "sql_assay_readthrough_constructs_with_measurements_rows.tex",
            sql="""
with m as (
  select
    construct_key,
    count(*) as n,
    avg(value) as mean_value,
    min(value) as min_value,
    max(value) as max_value
  from public.assay_measurements
  where measurement_type = 'readthrough_fraction' and value is not null
  group by 1
)
select
  c.assay_type,
  c.dataset,
  c.candidate_set,
  c.group_label,
  c.rank,
  c.stop_codon,
  c.k,
  m.n,
  m.mean_value,
  c.predicted_before_mean_delta,
  c.predicted_after_mean_delta,
  c.predicted_diff,
  c.plus4_nt,
  c.after_nt6,
  c.source_record_id,
  c.source_stop_base
from public.assay_constructs c
join m on m.construct_key = c.construct_key
where c.assay_type = 'readthrough'
order by c.stop_codon, c.k, c.predicted_diff desc nulls last, m.mean_value desc nulls last;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_codon_usage_decomp_U_aa_rows",
            out_tex=generated_dir() / "sql_refseq_codon_usage_decomp_U_aa_rows.tex",
            sql=f"""
select
  aa,
  n,
  obs_mean,
  null_mean,
  contrib
from public.codon_usage_null_decomp_aa
where panel = 'na'
  and dataset = '{str(args.refseq_dataset)}'
  and analysis_version = {ref_av}
  and metric = 'U'
order by abs(contrib) desc nulls last, aa;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_codon_usage_decomp_U_codon_rows",
            out_tex=generated_dir() / "sql_refseq_codon_usage_decomp_U_codon_rows.tex",
            sql=f"""
select
  codon,
  aa,
  obs_count,
  null_count,
  contrib
from public.codon_usage_null_decomp_codon
where panel = 'na'
  and dataset = '{str(args.refseq_dataset)}'
  and analysis_version = {ref_av}
  and metric = 'U'
order by abs(contrib) desc nulls last, codon;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_codon_usage_decomp_Z_aa_rows",
            out_tex=generated_dir() / "sql_refseq_codon_usage_decomp_Z_aa_rows.tex",
            sql=f"""
select
  aa,
  n,
  obs_mean,
  null_mean,
  contrib
from public.codon_usage_null_decomp_aa
where panel = 'na'
  and dataset = '{str(args.refseq_dataset)}'
  and analysis_version = {ref_av}
  and metric = 'Z'
order by abs(contrib) desc nulls last, aa;
""".strip(),
        ),
        QuerySpec(
            name="sql_refseq_codon_usage_decomp_Z_codon_rows",
            out_tex=generated_dir() / "sql_refseq_codon_usage_decomp_Z_codon_rows.tex",
            sql=f"""
select
  codon,
  aa,
  obs_count,
  null_count,
  contrib
from public.codon_usage_null_decomp_codon
where panel = 'na'
  and dataset = '{str(args.refseq_dataset)}'
  and analysis_version = {ref_av}
  and metric = 'Z'
order by abs(contrib) desc nulls last, codon;
""".strip(),
        ),
        QuerySpec(
            name="sql_recoding_multi_k_overall_rows",
            out_tex=generated_dir() / "sql_recoding_multi_k_overall_rows.tex",
            sql=f"""
select
  label,
  window_side,
  k,
  n1,
  n2,
  mean1,
  mean2,
  diff,
  ci_low,
  ci_high,
  hedges_g,
  p_welch,
  q_welch
from public.recoding_context_effects_multi_k
where dataset = '{rec_dataset_sql}'
  and analysis_version = {rec_av}
order by label, window_side, k;
""".strip(),
        ),
    ]

    pg8000_dbapi = _import_pg8000()
    sslmode = str(info.get("sslmode") or "require").lower()
    ssl_ctx = None if sslmode == "disable" else ssl.create_default_context()

    conn = pg8000_dbapi.connect(
        user=str(info["user"]),
        password=str(info.get("password") or ""),
        host=str(info["host"]),
        port=int(info["port"]),
        database=str(info["database"]),
        ssl_context=ssl_ctx,
    )
    try:
        # Best-effort DB state fingerprint for safe caching.
        # This avoids stale cache hits when the underlying tables change.
        state_fingerprint = {
            "recoding_sites_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.recoding_sites where analysis_version = %s and k = %s;",
                    (rec_av, rec_k),
                )
                or 0
            ),
            "corpus_panel_items_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.corpus_panel_items where panel = %s and analysis_version = %s;",
                    (str(args.panel_name), panel_av),
                )
                or 0
            ),
            "nonstandard_sequence_tests_items_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.nonstandard_sequence_tests_items where panel = %s and analysis_version = %s;",
                    (str(args.ns_panel), ns_av),
                )
                or 0
            ),
            "refseq_stop_context_comp_results_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.refseq_stop_context_comp_results where dataset = %s and analysis_version = %s and k = %s;",
                    (str(args.refseq_dataset), ref_av, ref_k),
                )
                or 0
            ),
            "refseq_stop_context_candidates_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.refseq_stop_context_candidates where dataset = %s and analysis_version = %s and candidate_set = %s and k = %s;",
                    (str(args.refseq_dataset), ref_av, str(ref_cand_set), ref_k),
                )
                or 0
            ),
            "refseq_stop_context_candidates_coding_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.refseq_stop_context_candidates where dataset = %s and analysis_version = %s and candidate_set = %s and k = %s;",
                    (str(args.refseq_dataset), ref_av, str(ref_cand_set_coding), ref_k),
                )
                or 0
            ),
            "boundary_enrichment_results_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.boundary_enrichment_results where analysis_version = %s;",
                    (enrich_av,),
                )
                or 0
            ),
            "analysis_runs_nonstandard_codes_n": int(
                _query_scalar(
                    conn,
                    "select count(*) from public.analysis_runs where dataset = %s and analysis = %s and analysis_version = %s;",
                    (str(nsc_dataset), "nonstandard_codes", nsc_av),
                )
                or 0
            ),
            "stop_context_pairwise_effects_n": int(_query_scalar(conn, "select count(*) from public.stop_context_pairwise_effects;", ()) or 0),
            "stop_context_means_n": int(_query_scalar(conn, "select count(*) from public.stop_context_means;", ()) or 0),
            "start_context_means_n": int(_query_scalar(conn, "select count(*) from public.start_context_means;", ()) or 0),
            "dataset_codon_usage_null_n": int(_query_scalar(conn, "select count(*) from public.dataset_codon_usage_null;", ()) or 0),
            "assay_constructs_n": int(_query_scalar(conn, "select count(*) from public.assay_constructs;", ()) or 0),
            "assay_measurements_n": int(_query_scalar(conn, "select count(*) from public.assay_measurements;", ()) or 0),
            "codon_usage_null_decomp_aa_n": int(_query_scalar(conn, "select count(*) from public.codon_usage_null_decomp_aa;", ()) or 0),
            "codon_usage_null_decomp_codon_n": int(
                _query_scalar(conn, "select count(*) from public.codon_usage_null_decomp_codon;", ()) or 0
            ),
            "recoding_context_effects_multi_k_n": int(
                _query_scalar(conn, "select count(*) from public.recoding_context_effects_multi_k;", ()) or 0
            ),
        }

        for q in queries:
            cache_key = {
                "analysis": "supabase_sql_fragments",
                "name": q.name,
                "db": db_public,
                "db_state": state_fingerprint,
                "sql_sha256": hashlib.sha256(q.sql.encode("utf-8")).hexdigest(),
            }
            cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

            if (not args.force) and q.out_tex.exists() and cache_hit(q.out_tex, expected_meta=cache_meta, require_meta=True):
                print(f"[cache] hit: {q.out_tex}")
                continue

            cur = conn.cursor()
            try:
                cur.execute(q.sql)
                rows = cur.fetchall() if cur.description is not None else []
            finally:
                cur.close()

            q.out_tex.write_text(_rows_to_tex(rows, bottomrule=True), encoding="utf-8")
            write_json_atomic(cache_meta_path(q.out_tex), cache_meta)
            print("Wrote:", q.out_tex)
    finally:
        conn.close()


if __name__ == "__main__":
    main()


