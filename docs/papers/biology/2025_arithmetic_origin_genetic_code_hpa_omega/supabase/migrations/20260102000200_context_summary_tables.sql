-- Context summary tables for cross-dataset meta-analysis (Supabase/Postgres).

-- -----------------------------------
-- Stop-context pairwise effects (U uplift windows)
-- -----------------------------------
create table if not exists public.stop_context_pairwise_effects (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null default 'na',          -- e.g. 'corpus_panel_v1', or 'na'
  dataset text not null,                    -- dataset label/key used by the importing pipeline
  analysis_version integer not null,

  window_side text not null,                -- 'before' or 'after'
  k integer not null,
  pair text not null,                       -- e.g. 'UAA_vs_UGA'

  n1 integer,
  n2 integer,
  mean1 double precision,
  mean2 double precision,
  diff double precision,
  ci_low double precision,
  ci_high double precision,
  cohen_d double precision,
  hedges_g double precision,
  z double precision,
  p double precision,
  q double precision,

  payload jsonb,

  constraint stop_context_pairwise_effects_window_side_chk check (window_side in ('before','after')),
  unique (panel, dataset, analysis_version, window_side, k, pair)
);

create index if not exists stop_context_pairwise_effects_panel_idx on public.stop_context_pairwise_effects (panel);
create index if not exists stop_context_pairwise_effects_dataset_idx on public.stop_context_pairwise_effects (dataset);
create index if not exists stop_context_pairwise_effects_av_idx on public.stop_context_pairwise_effects (analysis_version);
create index if not exists stop_context_pairwise_effects_k_idx on public.stop_context_pairwise_effects (k);
create index if not exists stop_context_pairwise_effects_pair_idx on public.stop_context_pairwise_effects (pair);
create index if not exists stop_context_pairwise_effects_p_idx on public.stop_context_pairwise_effects (p);


-- -----------------------------------
-- Stop-context window means (by stop codon and k)
-- -----------------------------------
create table if not exists public.stop_context_means (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null default 'na',
  dataset text not null,
  analysis_version integer not null,

  k integer not null,
  stop_codon text not null,

  n_before integer,
  before_mean double precision,
  n_after integer,
  after_mean double precision,

  payload jsonb,

  unique (panel, dataset, analysis_version, k, stop_codon)
);

create index if not exists stop_context_means_panel_idx on public.stop_context_means (panel);
create index if not exists stop_context_means_dataset_idx on public.stop_context_means (dataset);
create index if not exists stop_context_means_k_idx on public.stop_context_means (k);
create index if not exists stop_context_means_stop_codon_idx on public.stop_context_means (stop_codon);


-- -----------------------------------
-- Start-context window means (by dataset and k)
-- -----------------------------------
create table if not exists public.start_context_means (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null default 'na',
  dataset text not null,
  analysis_version integer not null,

  k integer not null,
  start_event text not null default 'AUG',  -- e.g. 'AUG' (best-ORF mode) or 'cds_start' (CDS FASTA mode)

  n_before integer,
  before_mean double precision,
  n_after integer,
  after_mean double precision,

  payload jsonb,

  unique (panel, dataset, analysis_version, k, start_event)
);

create index if not exists start_context_means_panel_idx on public.start_context_means (panel);
create index if not exists start_context_means_dataset_idx on public.start_context_means (dataset);
create index if not exists start_context_means_k_idx on public.start_context_means (k);
create index if not exists start_context_means_event_idx on public.start_context_means (start_event);


-- -----------------------------------
-- Codon-usage null test summary (amino-acid preserving)
-- -----------------------------------
create table if not exists public.dataset_codon_usage_null (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null default 'na',
  dataset text not null,
  analysis_version integer not null,

  obs_zbar double precision,
  obs_ubar double precision,
  null_mean_zbar double precision,
  null_sd_zbar double precision,
  null_mean_ubar double precision,
  null_sd_ubar double precision,
  z_zbar double precision,
  z_ubar double precision,
  p_zbar double precision,
  p_ubar double precision,
  total_codons bigint,

  payload jsonb,

  unique (panel, dataset, analysis_version)
);

create index if not exists dataset_codon_usage_null_panel_idx on public.dataset_codon_usage_null (panel);
create index if not exists dataset_codon_usage_null_dataset_idx on public.dataset_codon_usage_null (dataset);
create index if not exists dataset_codon_usage_null_av_idx on public.dataset_codon_usage_null (analysis_version);
create index if not exists dataset_codon_usage_null_p_idx on public.dataset_codon_usage_null (p_zbar, p_ubar);


