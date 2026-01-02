-- Codon-usage null decomposition tables (amino-acid and codon contributions).

create table if not exists public.codon_usage_null_decomp_aa (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null default 'na',
  dataset text not null,
  analysis_version integer not null,
  metric text not null, -- 'U' or 'Z'

  aa text not null,
  n bigint,
  obs_mean double precision,
  null_mean double precision,
  contrib double precision,

  payload jsonb,

  constraint codon_usage_null_decomp_aa_metric_chk check (metric in ('U','Z')),
  unique (panel, dataset, analysis_version, metric, aa)
);

create index if not exists codon_usage_null_decomp_aa_dataset_idx on public.codon_usage_null_decomp_aa (dataset);
create index if not exists codon_usage_null_decomp_aa_metric_idx on public.codon_usage_null_decomp_aa (metric);
create index if not exists codon_usage_null_decomp_aa_contrib_idx on public.codon_usage_null_decomp_aa (contrib);


create table if not exists public.codon_usage_null_decomp_codon (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  panel text not null default 'na',
  dataset text not null,
  analysis_version integer not null,
  metric text not null, -- 'U' or 'Z'

  codon text not null,
  aa text,
  obs_count bigint,
  null_count double precision,
  contrib double precision,

  payload jsonb,

  constraint codon_usage_null_decomp_codon_metric_chk check (metric in ('U','Z')),
  unique (panel, dataset, analysis_version, metric, codon)
);

create index if not exists codon_usage_null_decomp_codon_dataset_idx on public.codon_usage_null_decomp_codon (dataset);
create index if not exists codon_usage_null_decomp_codon_metric_idx on public.codon_usage_null_decomp_codon (metric);
create index if not exists codon_usage_null_decomp_codon_contrib_idx on public.codon_usage_null_decomp_codon (contrib);


