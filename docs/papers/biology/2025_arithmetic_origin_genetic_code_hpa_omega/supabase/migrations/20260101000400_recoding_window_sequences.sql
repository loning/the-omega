-- Add small window-sequence columns for recoding-site contexts (k codons each side, DNA alphabet).

alter table public.recoding_sites
  add column if not exists before_seq_dna text,
  add column if not exists after_seq_dna text;


