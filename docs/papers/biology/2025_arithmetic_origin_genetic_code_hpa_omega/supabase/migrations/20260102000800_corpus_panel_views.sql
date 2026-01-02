-- Views to support paper tables via PostgREST (HTTPS/443).

create or replace view public.corpus_panel_codon_usage_null_summary as
select
  p.panel,
  p.analysis_version,
  p.dataset,
  p.label,
  p.domain,
  p.mode,
  p.code_id,
  n.total_codons,
  n.obs_zbar,
  n.null_mean_zbar,
  (n.obs_zbar - n.null_mean_zbar) as delta_zbar,
  n.z_zbar,
  n.p_zbar,
  n.obs_ubar,
  n.null_mean_ubar,
  (n.obs_ubar - n.null_mean_ubar) as delta_ubar,
  n.z_ubar,
  n.p_ubar
from public.corpus_panel_items p
join public.dataset_codon_usage_null n
  on n.panel = p.panel
  and n.dataset = p.dataset
  and n.analysis_version = p.analysis_version
where p.present is true;


