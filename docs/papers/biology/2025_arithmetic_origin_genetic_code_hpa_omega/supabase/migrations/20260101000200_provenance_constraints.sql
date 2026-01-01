-- Tighten provenance-related constraints to make imports idempotent and consistent.

alter table public.recoding_sites
  alter column analysis_version set not null;

alter table public.refseq_stop_context_comp_results
  alter column analysis_version set not null;

alter table public.analysis_runs
  alter column analysis_version set not null;

-- Add only once (idempotent across repeated migration applications).
do $$
begin
  if not exists (
    select 1
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'analysis_runs'
      and c.conname = 'analysis_runs_dataset_analysis_version_uniq'
  ) then
    alter table public.analysis_runs
      add constraint analysis_runs_dataset_analysis_version_uniq unique (dataset, analysis, analysis_version);
  end if;
end
$$;


