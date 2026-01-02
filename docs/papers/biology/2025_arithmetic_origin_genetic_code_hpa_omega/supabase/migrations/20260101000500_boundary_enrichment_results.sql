-- Boundary enrichment test results (annotation-aligned).

create table if not exists public.boundary_enrichment_results (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  dataset text not null,
  analysis_version integer not null,
  label text not null,
  method text not null,

  n_total bigint,
  n_subset bigint,
  boundary_rate_total double precision,
  boundary_rate_subset double precision,
  enrichment double precision,
  p double precision,

  payload jsonb not null,

  unique (dataset, analysis_version, label, method)
);

create index if not exists boundary_enrichment_results_dataset_idx on public.boundary_enrichment_results (dataset);
create index if not exists boundary_enrichment_results_label_idx on public.boundary_enrichment_results (label);


