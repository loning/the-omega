-- Views for SQL-first, cross-dataset analysis that can be queried via PostgREST.

create or replace view public.stop_context_meta_effects as
with base as (
  select
    p.panel,
    p.analysis_version,
    p.domain,
    e.window_side,
    e.k,
    e.pair,
    e.diff,
    e.ci_low,
    e.ci_high
  from public.stop_context_pairwise_effects e
  join public.corpus_panel_items p
    on p.panel = e.panel
    and p.analysis_version = e.analysis_version
    and p.dataset = e.dataset
  where p.present is true
    and e.diff is not null
    and e.ci_low is not null
    and e.ci_high is not null
),
w as (
  select
    panel,
    analysis_version,
    domain,
    window_side,
    k,
    pair,
    diff,
    ((ci_high - ci_low) / (2.0 * 1.96)) as se,
    1.0 / power(((ci_high - ci_low) / (2.0 * 1.96)), 2) as weight
  from base
  where (ci_high - ci_low) > 0
),
agg as (
  select
    panel,
    analysis_version,
    domain,
    window_side,
    k,
    pair,
    count(*) as n_datasets,
    sum(weight * diff) / sum(weight) as meta_diff,
    sqrt(1.0 / sum(weight)) as meta_se
  from w
  group by 1,2,3,4,5,6
),
z as (
  select
    panel,
    analysis_version,
    domain,
    window_side,
    k,
    pair,
    n_datasets,
    meta_diff,
    meta_se,
    (meta_diff / meta_se) as z
  from agg
  where meta_se > 0
)
select
  panel,
  analysis_version,
  domain,
  window_side,
  k,
  pair,
  n_datasets,
  meta_diff,
  meta_se,
  z,
  2.0 * (1.0 - 0.5 * (1.0 + erf(abs(z) / sqrt(2.0)))) as p
from z;


