-- Assay tables for wet-lab validation (reporter readthrough / Sec / Pyl).

-- -----------------------------------
-- Assay constructs (sequence contexts + predicted features)
-- -----------------------------------
create table if not exists public.assay_constructs (
  construct_id uuid primary key default gen_random_uuid(),
  inserted_at timestamptz not null default now(),

  -- Deterministic key for idempotent upserts (computed by scripts, e.g. sha256 of context + assay_type).
  construct_key text not null,
  assay_type text not null,          -- e.g. 'readthrough', 'sec', 'pyl'

  dataset text,                      -- provenance label (optional)
  candidate_set text,                -- optional grouping label (e.g. 'reporter_v1')
  group_label text,                  -- optional selection group (e.g. 'matched_after_high')
  rank integer,                      -- optional rank within group
  k integer,                         -- window radius used to define before/after sequences and predicted means

  stop_codon text,                   -- optional (for stop-codon assays)
  before_seq_dna text,
  stop_codon_dna text,
  after_seq_dna text,
  plus4_nt text,
  after_nt6 text,

  predicted_before_mean_delta double precision,
  predicted_after_mean_delta double precision,
  predicted_diff double precision,
  predicted_before_gc double precision,
  predicted_after_gc double precision,
  predicted_before_dinuc jsonb,
  predicted_after_dinuc jsonb,

  source_record_id text,
  source_frame smallint,
  source_start_base integer,
  source_stop_base integer,

  payload jsonb,

  unique (construct_key)
);

create index if not exists assay_constructs_assay_type_idx on public.assay_constructs (assay_type);
create index if not exists assay_constructs_dataset_idx on public.assay_constructs (dataset);
create index if not exists assay_constructs_stop_codon_idx on public.assay_constructs (stop_codon);


-- -----------------------------------
-- Assay measurements (raw replicates or aggregated readouts)
-- -----------------------------------
create table if not exists public.assay_measurements (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),

  construct_key text not null references public.assay_constructs(construct_key) on delete cascade,
  batch text,                        -- optional experimental batch ID
  replicate integer,                 -- optional replicate index within batch

  measurement_type text not null,    -- e.g. 'readthrough_fraction', 'sec_incorporation', 'pyl_incorporation'
  value double precision,
  unit text,
  stderr double precision,
  n integer,

  payload jsonb,

  unique (construct_key, batch, replicate, measurement_type)
);

create index if not exists assay_measurements_type_idx on public.assay_measurements (measurement_type);
create index if not exists assay_measurements_batch_idx on public.assay_measurements (batch);


