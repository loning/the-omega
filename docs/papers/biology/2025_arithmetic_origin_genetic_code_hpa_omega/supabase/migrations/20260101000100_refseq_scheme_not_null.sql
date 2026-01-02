-- Ensure scheme is always present (avoid NULL semantics in UNIQUE constraints).
-- We use 'na' for NN-method rows where stratification scheme is not applicable.

alter table if exists public.refseq_stop_context_comp_results
  alter column scheme set default 'na';

update public.refseq_stop_context_comp_results
set scheme = 'na'
where scheme is null;

alter table public.refseq_stop_context_comp_results
  alter column scheme set not null;


