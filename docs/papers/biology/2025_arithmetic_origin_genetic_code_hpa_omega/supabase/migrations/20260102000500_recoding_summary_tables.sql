-- Recoding summary tables (multi-k overall effect summaries).

create table if not exists public.recoding_context_effects_multi_k (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  dataset text not null,             -- e.g. 'ncbi_recoding_genbank'
  analysis_version integer not null,

  k integer not null,
  window_side text not null,         -- 'before' or 'after'
  label text not null,               -- comparison label

  n1 integer,
  n2 integer,
  mean1 double precision,
  mean2 double precision,
  diff double precision,
  ci_low double precision,
  ci_high double precision,
  cohen_d double precision,
  hedges_g double precision,

  p_perm double precision,
  p_welch double precision,
  q_welch double precision,

  payload jsonb,

  constraint recoding_context_effects_multi_k_window_side_chk check (window_side in ('before','after')),
  unique (dataset, analysis_version, k, window_side, label)
);

create index if not exists recoding_context_effects_multi_k_dataset_idx on public.recoding_context_effects_multi_k (dataset);
create index if not exists recoding_context_effects_multi_k_k_idx on public.recoding_context_effects_multi_k (k);
create index if not exists recoding_context_effects_multi_k_label_idx on public.recoding_context_effects_multi_k (label);
create index if not exists recoding_context_effects_multi_k_p_idx on public.recoding_context_effects_multi_k (p_welch);


