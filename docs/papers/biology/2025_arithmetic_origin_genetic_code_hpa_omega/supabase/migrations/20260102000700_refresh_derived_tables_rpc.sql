-- SQL-first refresh of derived analysis tables from existing payload sources.
--
-- This enables a PostgREST RPC workflow (HTTPS/443) that does not require direct
-- Postgres connectivity from the client environment.

create or replace function public.refresh_paper_derived_tables(
  panel_name text default 'corpus_panel_v1',
  panel_av integer default 2,
  refseq_dataset text default 'human_refseq_mrna',
  refseq_av integer default 4,
  recoding_dataset text default 'ncbi_recoding_genbank',
  recoding_av integer default 7
)
returns jsonb
language plpgsql
as $$
declare
  v1 bigint := 0;
  v2 bigint := 0;
  v3 bigint := 0;
  v4 bigint := 0;
  v5 bigint := 0;
  v6 bigint := 0;
  v7 bigint := 0;
  v8 bigint := 0;
begin
  -- 1) dataset_codon_usage_null (RefSeq; from analysis_runs payload)
  insert into public.dataset_codon_usage_null(
    panel,dataset,analysis_version,
    obs_zbar,obs_ubar,
    null_mean_zbar,null_sd_zbar,
    null_mean_ubar,null_sd_ubar,
    z_zbar,z_ubar,
    p_zbar,p_ubar,
    total_codons,
    payload
  )
  select
    'na' as panel,
    ar.dataset,
    ar.analysis_version,
    (ar.payload->'codon_usage'->>'zbar')::double precision as obs_zbar,
    (ar.payload->'codon_usage'->>'ubar')::double precision as obs_ubar,
    (ar.payload->'codon_usage'->'null'->>'null_mu_zbar')::double precision as null_mean_zbar,
    (ar.payload->'codon_usage'->'null'->>'null_sd_zbar')::double precision as null_sd_zbar,
    (ar.payload->'codon_usage'->'null'->>'null_mu_ubar')::double precision as null_mean_ubar,
    (ar.payload->'codon_usage'->'null'->>'null_sd_ubar')::double precision as null_sd_ubar,
    (ar.payload->'codon_usage'->'null'->>'z_zbar')::double precision as z_zbar,
    (ar.payload->'codon_usage'->'null'->>'z_ubar')::double precision as z_ubar,
    (ar.payload->'codon_usage'->'null'->>'p_zbar')::double precision as p_zbar,
    (ar.payload->'codon_usage'->'null'->>'p_ubar')::double precision as p_ubar,
    floor((ar.payload->'codon_usage'->'null'->>'total_codons')::numeric)::bigint as total_codons,
    jsonb_build_object('analysis_runs', jsonb_build_object('dataset', ar.dataset, 'analysis', ar.analysis, 'analysis_version', ar.analysis_version)) as payload
  from public.analysis_runs ar
  where ar.dataset = refseq_dataset
    and ar.analysis = 'transcriptome_summary'
    and ar.analysis_version = refseq_av
  on conflict (panel,dataset,analysis_version) do update set
    obs_zbar=excluded.obs_zbar,
    obs_ubar=excluded.obs_ubar,
    null_mean_zbar=excluded.null_mean_zbar,
    null_sd_zbar=excluded.null_sd_zbar,
    null_mean_ubar=excluded.null_mean_ubar,
    null_sd_ubar=excluded.null_sd_ubar,
    z_zbar=excluded.z_zbar,
    z_ubar=excluded.z_ubar,
    p_zbar=excluded.p_zbar,
    p_ubar=excluded.p_ubar,
    total_codons=excluded.total_codons,
    payload=excluded.payload;
  get diagnostics v1 = row_count;

  -- 2) dataset_codon_usage_null (corpus panel; from corpus_panel_items payload)
  insert into public.dataset_codon_usage_null(
    panel,dataset,analysis_version,
    obs_zbar,obs_ubar,
    null_mean_zbar,null_sd_zbar,
    null_mean_ubar,null_sd_ubar,
    z_zbar,z_ubar,
    p_zbar,p_ubar,
    total_codons,
    payload
  )
  select
    c.panel,
    c.dataset,
    c.analysis_version,
    (c.payload->'codon_usage_null'->'Z'->>'obs_mean')::double precision as obs_zbar,
    (c.payload->'codon_usage_null'->'U'->>'obs_mean')::double precision as obs_ubar,
    (c.payload->'codon_usage_null'->'Z'->>'null_mean')::double precision as null_mean_zbar,
    (c.payload->'codon_usage_null'->'Z'->>'null_sd')::double precision as null_sd_zbar,
    (c.payload->'codon_usage_null'->'U'->>'null_mean')::double precision as null_mean_ubar,
    (c.payload->'codon_usage_null'->'U'->>'null_sd')::double precision as null_sd_ubar,
    (c.payload->'codon_usage_null'->'Z'->>'z')::double precision as z_zbar,
    (c.payload->'codon_usage_null'->'U'->>'z')::double precision as z_ubar,
    (c.payload->'codon_usage_null'->'Z'->>'p')::double precision as p_zbar,
    (c.payload->'codon_usage_null'->'U'->>'p')::double precision as p_ubar,
    c.coding_tokens as total_codons,
    c.payload->'codon_usage_null' as payload
  from public.corpus_panel_items c
  where c.panel = panel_name
    and c.analysis_version = panel_av
    and c.present is true
  on conflict (panel,dataset,analysis_version) do update set
    obs_zbar=excluded.obs_zbar,
    obs_ubar=excluded.obs_ubar,
    null_mean_zbar=excluded.null_mean_zbar,
    null_sd_zbar=excluded.null_sd_zbar,
    null_mean_ubar=excluded.null_mean_ubar,
    null_sd_ubar=excluded.null_sd_ubar,
    z_zbar=excluded.z_zbar,
    z_ubar=excluded.z_ubar,
    p_zbar=excluded.p_zbar,
    p_ubar=excluded.p_ubar,
    total_codons=excluded.total_codons,
    payload=excluded.payload;
  get diagnostics v2 = row_count;

  -- 3) stop_context_means (RefSeq)
  insert into public.stop_context_means(
    panel,dataset,analysis_version,k,stop_codon,
    n_before,before_mean,n_after,after_mean,
    payload
  )
  select
    'na' as panel,
    ar.dataset,
    ar.analysis_version,
    (kk.key)::int as k,
    stop.key as stop_codon,
    (kk.value->'before'->>'n')::int as n_before,
    (kk.value->'before'->>'mean')::double precision as before_mean,
    (kk.value->'after'->>'n')::int as n_after,
    (kk.value->'after'->>'mean')::double precision as after_mean,
    kk.value as payload
  from public.analysis_runs ar
  cross join lateral jsonb_each(ar.payload->'stop_context_welford_multi_k') stop
  cross join lateral jsonb_each(stop.value) kk
  where ar.dataset = refseq_dataset
    and ar.analysis = 'transcriptome_summary'
    and ar.analysis_version = refseq_av
  on conflict (panel,dataset,analysis_version,k,stop_codon) do update set
    n_before=excluded.n_before,
    before_mean=excluded.before_mean,
    n_after=excluded.n_after,
    after_mean=excluded.after_mean,
    payload=excluded.payload;
  get diagnostics v3 = row_count;

  -- 4) stop_context_means (corpus panel)
  insert into public.stop_context_means(
    panel,dataset,analysis_version,k,stop_codon,
    n_before,before_mean,n_after,after_mean,
    payload
  )
  select
    c.panel,
    c.dataset,
    c.analysis_version,
    (kpair.key)::int as k,
    stop.key as stop_codon,
    (stop.value->>'n')::int as n_before,
    (stop.value->>'before_mean')::double precision as before_mean,
    case when (stop.value ? 'after_mean') and (stop.value->>'after_mean') is not null then (stop.value->>'n')::int else 0 end as n_after,
    (stop.value->>'after_mean')::double precision as after_mean,
    stop.value as payload
  from public.corpus_panel_items c
  cross join lateral jsonb_each(c.payload->'summary'->'stop_context_multi_k') kpair
  cross join lateral jsonb_each(kpair.value) stop
  where c.panel = panel_name
    and c.analysis_version = panel_av
    and c.present is true
  on conflict (panel,dataset,analysis_version,k,stop_codon) do update set
    n_before=excluded.n_before,
    before_mean=excluded.before_mean,
    n_after=excluded.n_after,
    after_mean=excluded.after_mean,
    payload=excluded.payload;
  get diagnostics v4 = row_count;

  -- 5) start_context_means (RefSeq)
  insert into public.start_context_means(
    panel,dataset,analysis_version,k,start_event,
    n_before,before_mean,n_after,after_mean,
    payload
  )
  select
    'na' as panel,
    ar.dataset,
    ar.analysis_version,
    (kk.key)::int as k,
    'AUG' as start_event,
    (kk.value->'before'->>'n')::int as n_before,
    (kk.value->'before'->>'mean')::double precision as before_mean,
    (kk.value->'after'->>'n')::int as n_after,
    (kk.value->'after'->>'mean')::double precision as after_mean,
    kk.value as payload
  from public.analysis_runs ar
  cross join lateral jsonb_each(ar.payload->'start_context_welford_multi_k') kk
  where ar.dataset = refseq_dataset
    and ar.analysis = 'transcriptome_summary'
    and ar.analysis_version = refseq_av
  on conflict (panel,dataset,analysis_version,k,start_event) do update set
    n_before=excluded.n_before,
    before_mean=excluded.before_mean,
    n_after=excluded.n_after,
    after_mean=excluded.after_mean,
    payload=excluded.payload;
  get diagnostics v5 = row_count;

  -- 6) start_context_means (corpus panel)
  insert into public.start_context_means(
    panel,dataset,analysis_version,k,start_event,
    n_before,before_mean,n_after,after_mean,
    payload
  )
  select
    c.panel,
    c.dataset,
    c.analysis_version,
    (kk.key)::int as k,
    case when c.mode = 'refseq_mrna_best_orf' then 'AUG' else 'cds_start' end as start_event,
    (kk.value->'before'->>'n')::int as n_before,
    (kk.value->'before'->>'mean')::double precision as before_mean,
    (kk.value->'after'->>'n')::int as n_after,
    (kk.value->'after'->>'mean')::double precision as after_mean,
    kk.value as payload
  from public.corpus_panel_items c
  cross join lateral jsonb_each(c.payload->'summary'->'start_context_multi_k') kk
  where c.panel = panel_name
    and c.analysis_version = panel_av
    and c.present is true
  on conflict (panel,dataset,analysis_version,k,start_event) do update set
    n_before=excluded.n_before,
    before_mean=excluded.before_mean,
    n_after=excluded.n_after,
    after_mean=excluded.after_mean,
    payload=excluded.payload;
  get diagnostics v6 = row_count;

  -- 7) stop_context_pairwise_effects (corpus panel; BH q within each dataset)
  with raw as (
    select
      c.panel,
      c.dataset,
      c.analysis_version,
      ws.key as window_side,
      (kk.key)::int as k,
      pair.key as pair,
      (pair.value->>'n1')::int as n1,
      (pair.value->>'n2')::int as n2,
      (pair.value->>'mean1')::double precision as mean1,
      (pair.value->>'mean2')::double precision as mean2,
      (pair.value->>'diff')::double precision as diff,
      (pair.value->>'ci_low')::double precision as ci_low,
      (pair.value->>'ci_high')::double precision as ci_high,
      (pair.value->>'d')::double precision as cohen_d,
      (pair.value->>'g')::double precision as hedges_g,
      (pair.value->>'z')::double precision as z,
      (pair.value->>'p')::double precision as p,
      pair.value as payload
    from public.corpus_panel_items c
    cross join lateral jsonb_each(c.payload->'summary'->'stop_context_effects_multi_k') ws
    cross join lateral jsonb_each(ws.value) kk
    cross join lateral jsonb_each(kk.value) pair
    where c.panel = panel_name
      and c.analysis_version = panel_av
      and c.present is true
      and (pair.value ? 'p')
      and (pair.value->>'p') is not null
  ),
  ranked as (
    select
      raw.*,
      count(*) over (partition by panel,dataset,analysis_version) as m,
      row_number() over (partition by panel,dataset,analysis_version order by p asc, window_side, k, pair) as r,
      (p * count(*) over (partition by panel,dataset,analysis_version) /
        row_number() over (partition by panel,dataset,analysis_version order by p asc, window_side, k, pair)
      ) as q_raw
    from raw
  ),
  q as (
    select
      ranked.*,
      least(1.0, min(q_raw) over (partition by panel,dataset,analysis_version order by p asc rows between current row and unbounded following)) as q
    from ranked
  )
  insert into public.stop_context_pairwise_effects(
    panel,dataset,analysis_version,window_side,k,pair,
    n1,n2,mean1,mean2,diff,ci_low,ci_high,cohen_d,hedges_g,z,p,q,
    payload
  )
  select
    panel,dataset,analysis_version,window_side,k,pair,
    n1,n2,mean1,mean2,diff,ci_low,ci_high,cohen_d,hedges_g,z,p,q,
    payload
  from q
  on conflict (panel,dataset,analysis_version,window_side,k,pair) do update set
    n1=excluded.n1,
    n2=excluded.n2,
    mean1=excluded.mean1,
    mean2=excluded.mean2,
    diff=excluded.diff,
    ci_low=excluded.ci_low,
    ci_high=excluded.ci_high,
    cohen_d=excluded.cohen_d,
    hedges_g=excluded.hedges_g,
    z=excluded.z,
    p=excluded.p,
    q=excluded.q,
    payload=excluded.payload;
  get diagnostics v7 = row_count;

  -- 8) recoding_context_effects_multi_k (from analysis_runs payload; BH q over all rows)
  with run as (
    select dataset, analysis_version, payload
    from public.analysis_runs
    where dataset = recoding_dataset
      and analysis = 'recoding_sites_summary'
      and analysis_version = recoding_av
    order by inserted_at desc
    limit 1
  ),
  items as (
    select dataset, analysis_version, jsonb_array_elements(payload->'multi_k_overall') as it
    from run
  ),
  raw as (
    select
      dataset,
      analysis_version,
      (it->>'k')::int as k,
      (it->>'label')::text as label,
      side as window_side,
      (w->>'n1')::int as n1,
      (w->>'n2')::int as n2,
      (w->>'mean1')::double precision as mean1,
      (w->>'mean2')::double precision as mean2,
      (w->>'diff')::double precision as diff,
      (w->>'ci_low')::double precision as ci_low,
      (w->>'ci_high')::double precision as ci_high,
      (w->>'d')::double precision as cohen_d,
      (w->>'g')::double precision as hedges_g,
      (w->>'p_perm')::double precision as p_perm,
      (w->>'p_welch')::double precision as p_welch,
      w as payload
    from items
    cross join lateral (values ('before'),('after')) as s(side)
    cross join lateral (select (it->s.side) as w) as ww
    where (it->>'k') is not null and (it->>'label') is not null
      and (ww.w ? 'p_welch')
  ),
  ranked as (
    select
      raw.*,
      count(*) over () as m,
      row_number() over (order by p_welch asc, window_side, k, label) as r,
      (p_welch * count(*) over () / row_number() over (order by p_welch asc, window_side, k, label)) as q_raw
    from raw
  ),
  q as (
    select
      ranked.*,
      least(1.0, min(q_raw) over (order by p_welch asc rows between current row and unbounded following)) as q_welch
    from ranked
  )
  insert into public.recoding_context_effects_multi_k(
    dataset,analysis_version,k,window_side,label,
    n1,n2,mean1,mean2,diff,ci_low,ci_high,cohen_d,hedges_g,
    p_perm,p_welch,q_welch,
    payload
  )
  select
    dataset,analysis_version,k,window_side,label,
    n1,n2,mean1,mean2,diff,ci_low,ci_high,cohen_d,hedges_g,
    p_perm,p_welch,q_welch,
    payload
  from q
  on conflict (dataset,analysis_version,k,window_side,label) do update set
    n1=excluded.n1,
    n2=excluded.n2,
    mean1=excluded.mean1,
    mean2=excluded.mean2,
    diff=excluded.diff,
    ci_low=excluded.ci_low,
    ci_high=excluded.ci_high,
    cohen_d=excluded.cohen_d,
    hedges_g=excluded.hedges_g,
    p_perm=excluded.p_perm,
    p_welch=excluded.p_welch,
    q_welch=excluded.q_welch,
    payload=excluded.payload;
  get diagnostics v8 = row_count;

  return jsonb_build_object(
    'ok', true,
    'panel_name', panel_name,
    'panel_av', panel_av,
    'refseq_dataset', refseq_dataset,
    'refseq_av', refseq_av,
    'recoding_dataset', recoding_dataset,
    'recoding_av', recoding_av,
    'rowcount', jsonb_build_object(
      'dataset_codon_usage_null_refseq', v1,
      'dataset_codon_usage_null_panel', v2,
      'stop_context_means_refseq', v3,
      'stop_context_means_panel', v4,
      'start_context_means_refseq', v5,
      'start_context_means_panel', v6,
      'stop_context_pairwise_effects_panel', v7,
      'recoding_context_effects_multi_k', v8
    )
  );
end;
$$;


