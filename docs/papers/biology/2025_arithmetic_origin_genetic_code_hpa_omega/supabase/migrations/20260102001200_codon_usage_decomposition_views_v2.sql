-- Codon-usage null decomposition (U=delta) for corpus panel items (v2).
--
-- This version parameterizes synonymous sets by NCBI code_id using public.codon_translation_by_code,
-- so that code4 (UGA->Trp) can be handled consistently.

create or replace view public.corpus_panel_u_decomp_codon as
with panel as (
  select
    panel,
    analysis_version,
    dataset,
    label,
    domain,
    mode,
    code_id,
    payload
  from public.corpus_panel_items
  where present is true
    and code_id in (1,4,11)
),
aa_counts as (
  select
    p.panel,
    p.analysis_version,
    p.dataset,
    kv.key as aa,
    (kv.value)::bigint as aa_count
  from panel p
  cross join lateral jsonb_each_text(p.payload->'summary'->'aa_counts') kv
),
totals as (
  select
    panel,
    analysis_version,
    dataset,
    sum(aa_count) filter (where aa <> 'Stop') as total_codons
  from aa_counts
  group by 1,2,3
),
syn as (
  select
    t.code_id,
    t.aa,
    count(*) as n_syn,
    avg(f.delta)::double precision as null_mean_u
  from public.codon_translation_by_code t
  join public.codon_fold6_mu_star f on f.codon = t.codon
  where t.aa <> 'Stop'
  group by 1,2
),
codon_counts as (
  select
    p.panel,
    p.analysis_version,
    p.dataset,
    kv.key as codon,
    (kv.value)::bigint as obs_count
  from panel p
  cross join lateral jsonb_each_text(p.payload->'summary'->'codon_counts') kv
),
base as (
  select
    p.panel,
    p.analysis_version,
    p.dataset,
    p.label,
    p.domain,
    p.mode,
    p.code_id,
    t.codon,
    t.aa,
    f.delta as u_value,
    coalesce(cc.obs_count, 0)::bigint as obs_count,
    coalesce(ac.aa_count, 0)::bigint as aa_count,
    s.n_syn::int as n_syn,
    tot.total_codons::bigint as total_codons
  from panel p
  join public.codon_translation_by_code t
    on t.code_id = p.code_id
  join public.codon_fold6_mu_star f
    on f.codon = t.codon
  left join codon_counts cc
    on cc.panel = p.panel and cc.analysis_version = p.analysis_version and cc.dataset = p.dataset and cc.codon = t.codon
  left join aa_counts ac
    on ac.panel = p.panel and ac.analysis_version = p.analysis_version and ac.dataset = p.dataset and ac.aa = t.aa
  join syn s
    on s.code_id = p.code_id and s.aa = t.aa
  join totals tot
    on tot.panel = p.panel and tot.analysis_version = p.analysis_version and tot.dataset = p.dataset
  where t.aa <> 'Stop'
)
select
  panel,
  analysis_version,
  dataset,
  label,
  domain,
  mode,
  code_id,
  codon,
  aa,
  obs_count,
  (aa_count::double precision / nullif(n_syn::double precision, 0.0)) as exp_count,
  u_value,
  (((obs_count::double precision - (aa_count::double precision / nullif(n_syn::double precision, 0.0))) * u_value::double precision) / nullif(total_codons::double precision, 0.0)) as contrib_u
from base;


create or replace view public.corpus_panel_u_decomp_aa as
with cod as (
  select * from public.corpus_panel_u_decomp_codon
),
syn as (
  select
    code_id,
    aa,
    avg(u_value)::double precision as null_mean_u
  from cod
  group by 1,2
),
aa_totals as (
  select
    panel,
    analysis_version,
    dataset,
    sum(obs_count) as total_codons
  from cod
  group by 1,2,3
),
aa_obs as (
  select
    panel,
    analysis_version,
    dataset,
    label,
    domain,
    mode,
    code_id,
    aa,
    sum(obs_count) as n,
    (sum(obs_count::double precision * u_value::double precision) / nullif(sum(obs_count)::double precision, 0.0)) as obs_mean_u
  from cod
  group by 1,2,3,4,5,6,7,8
)
select
  a.panel,
  a.analysis_version,
  a.dataset,
  a.label,
  a.domain,
  a.mode,
  a.code_id,
  a.aa,
  a.n,
  a.obs_mean_u,
  s.null_mean_u,
  ((a.n::double precision / nullif(t.total_codons::double precision, 0.0)) * (a.obs_mean_u - s.null_mean_u)) as contrib_u
from aa_obs a
join syn s
  on s.code_id = a.code_id and s.aa = a.aa
join aa_totals t
  on t.panel = a.panel and t.analysis_version = a.analysis_version and t.dataset = a.dataset;


create or replace view public.corpus_panel_u_decomp_aa_top5 as
select *
from (
  select
    *,
    row_number() over (partition by panel, analysis_version, dataset order by abs(contrib_u) desc, aa asc) as rn
  from public.corpus_panel_u_decomp_aa
) ranked
where rn <= 5;


create or replace view public.corpus_panel_u_decomp_codon_top10 as
select *
from (
  select
    *,
    row_number() over (partition by panel, analysis_version, dataset order by abs(contrib_u) desc, codon asc) as rn
  from public.corpus_panel_u_decomp_codon
) ranked
where rn <= 10;


