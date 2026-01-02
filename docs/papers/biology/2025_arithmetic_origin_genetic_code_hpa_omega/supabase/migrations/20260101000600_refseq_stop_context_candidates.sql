-- RefSeq terminal-stop context candidate sets (for reporter assay design).

create table if not exists public.refseq_stop_context_candidates (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  dataset text not null,
  analysis_version integer not null,
  candidate_set text not null,
  k integer not null,

  stop_codon text not null,
  group_label text not null,
  rank integer,

  record_id text,
  frame smallint,
  start_base integer,
  stop_base integer,

  before_seq_dna text,
  stop_codon_dna text,
  after_seq_dna text,
  plus4_nt text,
  after_nt6 text,

  before_mean_delta double precision,
  after_mean_delta double precision,
  diff double precision,

  before_gc double precision,
  after_gc double precision,
  before_dinuc jsonb,
  after_dinuc jsonb,

  payload jsonb not null,

  unique (dataset, analysis_version, candidate_set, k, stop_codon, group_label, record_id, stop_base)
);

create index if not exists refseq_stop_context_candidates_dataset_idx on public.refseq_stop_context_candidates (dataset);
create index if not exists refseq_stop_context_candidates_stop_idx on public.refseq_stop_context_candidates (stop_codon);
create index if not exists refseq_stop_context_candidates_group_idx on public.refseq_stop_context_candidates (group_label);
create index if not exists refseq_stop_context_candidates_candidate_set_idx on public.refseq_stop_context_candidates (candidate_set);


