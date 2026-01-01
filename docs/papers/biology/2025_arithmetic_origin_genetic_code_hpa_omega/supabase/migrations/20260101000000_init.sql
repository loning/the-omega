-- Core research tables for Zeckendorf–Hilbert genetic-code paper (Supabase/Postgres).
-- This migration is safe to apply on a fresh Supabase project (local or cloud).

create extension if not exists pgcrypto;

-- ----------------------------
-- Recoding sites (GenBank transl_except)
-- ----------------------------
create table if not exists public.recoding_sites (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  analysis_version integer,
  k integer not null,

  version text not null,
  definition text,
  organism text,
  domain text,
  gene text,
  product text,

  cds_location text,
  cds_start integer,
  cds_end integer,
  cds_strand smallint,
  translation_start integer,

  aa text,
  pos_start integer not null,
  pos_end integer not null,
  codon_dna text,
  codon_rna text,

  n integer,
  w text,
  v integer,
  delta integer,
  is_boundary boolean,

  before_mean_delta double precision,
  after_mean_delta double precision,

  terminal_stop text,
  terminal_before_mean_delta double precision,
  terminal_after_mean_delta double precision,

  control_same_codon_before_mean_delta double precision,
  control_same_codon_after_mean_delta double precision,
  control_random_cds_before_mean_delta double precision,
  control_random_cds_after_mean_delta double precision,

  -- Composition (recoding windows)
  before_gc double precision,
  after_gc double precision,
  before_cpg double precision,
  after_cpg double precision,
  before_ta double precision,
  after_ta double precision,
  before_dinuc jsonb,
  after_dinuc jsonb,

  -- Composition (terminal-stop windows)
  terminal_before_gc double precision,
  terminal_after_gc double precision,
  terminal_before_cpg double precision,
  terminal_after_cpg double precision,
  terminal_before_ta double precision,
  terminal_after_ta double precision,
  terminal_before_dinuc jsonb,
  terminal_after_dinuc jsonb,

  -- NN matched controls (within-CDS pool)
  nn_ctrl_before_mean_delta double precision,
  nn_ctrl_after_mean_delta double precision,
  nn_before_diff double precision,
  nn_after_diff double precision,
  nn_before_l1 double precision,
  nn_after_l1 double precision,
  nn_before_gc_diff double precision,
  nn_after_gc_diff double precision,
  nn_before_gc_eps double precision,
  nn_after_gc_eps double precision,

  unique (analysis_version, k, version, pos_start)
);

create index if not exists recoding_sites_version_idx on public.recoding_sites (version);
create index if not exists recoding_sites_domain_idx on public.recoding_sites (domain);
create index if not exists recoding_sites_aa_idx on public.recoding_sites (aa);
create index if not exists recoding_sites_codon_idx on public.recoding_sites (codon_rna);
create index if not exists recoding_sites_boundary_idx on public.recoding_sites (is_boundary);

-- ----------------------------
-- RefSeq stop-context composition-adjusted results (aggregated)
-- ----------------------------
create table if not exists public.refseq_stop_context_comp_results (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  dataset text not null,
  analysis_version integer,
  k integer not null,

  method text not null,      -- 'stratified' or 'nn'
  scheme text,               -- e.g. 'gc_cpg', 'gc_ta' (null for nn)
  window_side text not null, -- 'before' or 'after'
  pair text not null,        -- e.g. 'UAA_vs_UGA'

  diff double precision,
  p double precision,

  -- stratified meta-analysis fields
  se double precision,
  z double precision,
  bins_used integer,

  -- nn sample cross-check fields
  n integer,
  ci_low double precision,
  ci_high double precision,

  unique (dataset, k, method, scheme, window_side, pair)
);

create index if not exists refseq_stop_context_comp_results_dataset_idx on public.refseq_stop_context_comp_results (dataset);
create index if not exists refseq_stop_context_comp_results_k_idx on public.refseq_stop_context_comp_results (k);
create index if not exists refseq_stop_context_comp_results_pair_idx on public.refseq_stop_context_comp_results (pair);

-- Optional: store whole run summaries as JSON for provenance.
create table if not exists public.analysis_runs (
  run_id uuid primary key default gen_random_uuid(),
  inserted_at timestamptz not null default now(),

  dataset text not null,
  analysis text not null,
  analysis_version integer,
  payload jsonb not null
);

create index if not exists analysis_runs_dataset_analysis_idx on public.analysis_runs (dataset, analysis);


