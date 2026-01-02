-- Codon -> amino-acid translation mapping for selected NCBI genetic codes.
--
-- We expose it as a VIEW so that other views can parameterize by code_id.
-- Currently supported:
--   - 1  (Standard)
--   - 11 (Bacterial/Archaeal)
--   - 4  (Mycoplasma/Spiroplasma): UGA codes for Trp (not Stop)

create or replace view public.codon_translation_by_code as
-- code 1
select
  1::int as code_id,
  codon,
  aa,
  (aa = 'Stop') as is_stop
from public.codon_fold6_mu_star

union all
-- code 11 (same mapping as standard for codon->AA labels in this project)
select
  11::int as code_id,
  codon,
  aa,
  (aa = 'Stop') as is_stop
from public.codon_fold6_mu_star

union all
-- code 4: UGA -> Trp; stop set is {UAA, UAG}
select
  4::int as code_id,
  codon,
  case when codon = 'UGA' then 'Trp' else aa end as aa,
  (codon in ('UAA','UAG')) as is_stop
from public.codon_fold6_mu_star;


