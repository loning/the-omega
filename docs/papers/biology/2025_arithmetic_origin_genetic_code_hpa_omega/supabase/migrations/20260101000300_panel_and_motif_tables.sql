-- Panel / nonstandard result tables for reproducible, queryable exports.
-- Also add new recoding-site mechanism columns (+4 base and short downstream motifs).

-- ----------------------------
-- Corpus panel items (per-dataset results)
-- ----------------------------
create table if not exists public.corpus_panel_items (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null,
  analysis_version integer not null,

  dataset text not null,
  code_id integer not null,
  label text,
  domain text,
  mode text,
  present boolean not null default false,

  -- Selected numeric summaries (when present=true; may be NULL otherwise)
  records integer,
  records_with_orf integer,
  coding_tokens bigint,
  boundary_token_count bigint,
  boundary_rate double precision,

  -- Full JSON payload for provenance / re-rendering
  payload jsonb not null,

  unique (panel, analysis_version, dataset, code_id)
);

create index if not exists corpus_panel_items_panel_idx on public.corpus_panel_items (panel);
create index if not exists corpus_panel_items_dataset_idx on public.corpus_panel_items (dataset);
create index if not exists corpus_panel_items_domain_idx on public.corpus_panel_items (domain);
create index if not exists corpus_panel_items_code_idx on public.corpus_panel_items (code_id);


-- ----------------------------
-- Nonstandard sequence-level tests (per-dataset results)
-- ----------------------------
create table if not exists public.nonstandard_sequence_tests_items (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null,
  analysis_version integer not null,

  dataset text not null,
  code_id integer not null,
  label text,
  domain text,
  present boolean not null default false,

  records_seen integer,
  records_used integer,
  records_invalid integer,

  start_boundary_rate double precision,
  start_boundary_z double precision,
  start_boundary_p double precision,

  stop_boundary_rate double precision,
  stop_boundary_z double precision,
  stop_boundary_p double precision,

  payload jsonb not null,

  unique (panel, analysis_version, dataset, code_id)
);

create index if not exists nonstandard_sequence_tests_items_panel_idx on public.nonstandard_sequence_tests_items (panel);
create index if not exists nonstandard_sequence_tests_items_dataset_idx on public.nonstandard_sequence_tests_items (dataset);
create index if not exists nonstandard_sequence_tests_items_domain_idx on public.nonstandard_sequence_tests_items (domain);
create index if not exists nonstandard_sequence_tests_items_code_idx on public.nonstandard_sequence_tests_items (code_id);


-- ----------------------------
-- Recoding-site mechanism columns (output by exp_recoding_sites.py analysis v6+)
-- ----------------------------
alter table public.recoding_sites
  add column if not exists plus4_nt text,
  add column if not exists after_codon1 text,
  add column if not exists after_nt6 text;

create index if not exists recoding_sites_plus4_nt_idx on public.recoding_sites (plus4_nt);

