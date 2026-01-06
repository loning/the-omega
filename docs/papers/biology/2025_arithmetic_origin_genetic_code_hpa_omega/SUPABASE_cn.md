### Supabase 数据库（Postgres）搭建与导入

本项目提供了可直接用于 Supabase 的 schema migration，以及把实验输出导出为 CSV 的脚本，便于在 Postgres 里做可查询、可复现的统计分析。

### 目录

- **schema/migration**：`supabase/migrations/`（按时间顺序执行）
- **导出脚本**：`scripts/export_supabase_tables.py`

### 云端 Supabase（已连接）最短流程（推荐）

本项目仅支持云端 Supabase，并默认你已经在 `supabase.env` 中配置好 `SUPABASE_URL` / `SUPABASE_KEY`。建议按以下最短流程执行（全程走 HTTPS/443，不依赖 5432）：

1) **导入基础表与 provenance（如需更新）**

在项目根目录 `docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega` 下运行：

```bash
python3 scripts/import_supabase_rest.py --batch-size 200
```

如果你已经导入过且产物未变化，可跳过本步；脚本自带导入级缓存，也可用 `--force` 强制重导。

2) **刷新派生表（在 Supabase 内部执行 SQL）**

```bash
python3 scripts/exp_supabase_refresh_derived_tables.py
```

3) **从派生表/视图生成论文 `.tex` 片段（写入 `sections/generated/`）**

```bash
python3 scripts/exp_supabase_rest_fragments.py --force
```

### 云端 Supabase（建库 / 迁移）

- **创建项目**：在 Supabase 控制台创建项目（Postgres）
- **应用 migration**：用 Supabase SQL Editor 按顺序执行 `supabase/migrations/*.sql`（或用 psql 连接后依次执行这些文件）

### Python 直连导入（PostgREST / REST，无需 psql）

本仓库提供了一个**纯标准库**的导入脚本，直接走 Supabase 的 PostgREST 接口写入多张表（含 provenance 的 `analysis_runs`）。

1) **确认连接信息文件（git ignore）**

- 默认使用项目根目录的 `supabase.env`（已配置）。
- 至少包含：
  - `SUPABASE_URL`
  - `SUPABASE_KEY`（建议使用可写入数据库的 key）
- `DATABASE_URL` 可选（仅用于你自己用 psql/驱动直连时）。
- 如缺失，可参考 `supabase.env.template` 补齐字段。

2) **执行导入**

在项目根目录 `docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega` 下运行：

```bash
python3 scripts/import_supabase_rest.py --batch-size 200
```

脚本带**导入级缓存**：对每张表根据输入产物（及其 `.meta.json`）计算 digest，重复运行会自动跳过已导入的同一批产物；如需强制重导可加 `--force`。长时间导入默认每 60 秒输出一次进度，可用 `--heartbeat-s` 调整（或设为 0 关闭）。

如果你的 Python 环境遇到证书链问题，可临时加 `--insecure`（仅用于本机证书缺失的场景）：

```bash
python3 scripts/import_supabase_rest.py --batch-size 200 --insecure
```

3) **可选：指定输入文件（支持 quick 产物）**

默认使用：

- `data/recoding_genbank/recoding_sites.jsonl`
- `data/recoding_genbank/recoding_sites_summary.json`
- `data/refseq_hsapiens_mrna/transcriptome_summary.json`
- `data/refseq_hsapiens_mrna/stop_context_pairwise_effects.tsv`
- `data/panel/corpus_panel_summary.json`
- `data/nonstandard_sequence_tests.json`

如果你跑的是快速流程（例如 `data/_quick/run_all/` 下的产物），可显式指定路径：

```bash
python3 scripts/import_supabase_rest.py \
  --recoding-jsonl data/_quick/run_all/recoding_sites.jsonl \
  --recoding-summary-json data/_quick/run_all/recoding_sites_summary.json \
  --refseq-summary-json data/_quick/run_all/transcriptome_summary.json \
  --panel-summary-json data/_quick/run_all/corpus_panel_summary.json \
  --nonstandard-seqtests-json data/_quick/run_all/nonstandard_sequence_tests.json \
  --batch-size 200
```

如 quick 的 `transcriptome_summary.json` 未包含 `stop_context_composition`（较旧 schema），可加 `--no-refseq` 仅导入 `recoding_sites` 与 `analysis_runs`：

```bash
python3 scripts/import_supabase_rest.py \
  --no-refseq \
  --recoding-jsonl data/_quick/run_all/recoding_sites.jsonl \
  --recoding-summary-json data/_quick/run_all/recoding_sites_summary.json \
  --refseq-summary-json data/_quick/run_all/transcriptome_summary.json \
  --batch-size 200
```

### Python 直连 Postgres 执行 SQL（强制 SQL 写在脚本中，用于生成 .tex）

本项目要求：**所有用于论文的 SQL 必须写在 Python 脚本中**（便于版本控制与复现），脚本执行 SQL 并把结果写入 `sections/generated/` 的 `.tex` 片段（带缓存，避免重复查询）。

1) **准备连接串**

- 在 `supabase.env` 中填写 `DATABASE_URL=postgresql://...`（参考 `supabase.env.template`）。

2) **安装依赖（虚拟环境）**

本项目使用纯 Python 驱动 `pg8000`：

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

3) **执行脚本生成 `.tex` 片段**

`scripts/exp_supabase_sql_fragments.py` 内部直接写入 SQL，生成若干 `sections/generated/sql_*.tex` 片段，并对每个片段做缓存：

```bash
./.venv/bin/python scripts/exp_supabase_sql_fragments.py
```

4) **如果 5432 无法直连（推荐备用）**

某些网络环境会阻断对 `db.<project>.supabase.co:5432` 的访问（常见报错：`No route to host`）。此时可改用 **PostgREST(HTTPS/443)** 拉取数据库内已存在的表/视图产物来生成 `.tex`：

- 依赖：`SUPABASE_URL` / `SUPABASE_KEY`（见 `supabase.env`）
- 不需要：`DATABASE_URL`

```bash
python3 scripts/exp_supabase_rest_fragments.py --force
```

### 通过 RPC 刷新派生表（仅 supabase.env，走 HTTPS/443）

如果你已经把 `analysis_runs` / `corpus_panel_items` 等 payload 数据导入 Supabase，但还没有把它们“展开”为论文用的派生表（例如 `dataset_codon_usage_null`、`stop_context_means`、`start_context_means`、`stop_context_pairwise_effects`、`recoding_context_effects_multi_k`），可用 Supabase 内置 RPC 一键刷新：

```bash
python3 scripts/exp_supabase_refresh_derived_tables.py
```

推荐的最短流程：

1) `python3 scripts/import_supabase_rest.py ...`（导入基础表 / analysis_runs）
2) `python3 scripts/exp_supabase_refresh_derived_tables.py`（在 Supabase 内部执行 SQL，刷新派生表）
3) `python3 scripts/exp_supabase_rest_fragments.py --force`（从表/视图拉取结果生成 `sections/generated/*.tex`）

### Corpus panel：codon-usage null 分解（\(\overline{U}\)）

项目中提供了 corpus panel 的 \(\overline{U}\) 偏差分解（AA top-5 / codon top-10），用于解释 \(\overline{U}-\mathbb{E}[\overline{U}]\) 的主要贡献来源。

- 当前支持的 `code_id`：**1 / 11 / 4**（其中 **code4** 采用 NCBI 定义的特例：`UGA -> Trp`，不作为 Stop）。

### 导出 CSV

- **导出**（在项目根目录 `docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega` 下运行）：

```bash
python3 scripts/export_supabase_tables.py --out-dir data/db_exports
```

如需从 quick 产物导出（例如 `data/_quick/run_all/`），可指定输入路径：

```bash
python3 scripts/export_supabase_tables.py \
  --recoding-jsonl data/_quick/run_all/recoding_sites.jsonl \
  --refseq-summary-json data/_quick/run_all/transcriptome_summary.json \
  --panel-summary-json data/_quick/run_all/corpus_panel_summary.json \
  --nonstandard-seqtests-json data/_quick/run_all/nonstandard_sequence_tests.json \
  --out-dir data/db_exports
```

如 quick 的 `transcriptome_summary.json` 未包含 `stop_context_composition`，可加 `--no-refseq` 仅导出 `recoding_sites.csv`：

```bash
python3 scripts/export_supabase_tables.py \
  --no-refseq \
  --recoding-jsonl data/_quick/run_all/recoding_sites.jsonl \
  --out-dir data/db_exports
```

会生成：
- `data/db_exports/recoding_sites.csv`
- `data/db_exports/refseq_stop_context_comp_results.csv`
- （可选）`data/db_exports/refseq_stop_context_candidates.csv`
- `data/db_exports/corpus_panel_items.csv`
- `data/db_exports/nonstandard_sequence_tests_items.csv`
- （可选）`data/db_exports/boundary_enrichment_results.csv`
- `data/db_exports/stop_context_pairwise_effects.csv`
- `data/db_exports/stop_context_means.csv`
- `data/db_exports/start_context_means.csv`
- `data/db_exports/dataset_codon_usage_null.csv`
- `data/db_exports/codon_usage_null_decomp_aa.csv`
- `data/db_exports/codon_usage_null_decomp_codon.csv`
- `data/db_exports/recoding_context_effects_multi_k.csv`

### 产物一致性校验（推荐）

在导入前可先做一次本地一致性检查（文件存在性、analysis\_version 一致性、冲突键重复等）：

```bash
python3 scripts/validate_artifacts.py
```

针对 quick 产物：

```bash
python3 scripts/validate_artifacts.py \
  --recoding-jsonl data/_quick/run_all/recoding_sites.jsonl \
  --recoding-summary-json data/_quick/run_all/recoding_sites_summary.json \
  --refseq-summary-json data/_quick/run_all/transcriptome_summary.json
```

如果 quick 未产生 recoding 行，可用 `--no-recoding` 仅校验 RefSeq summary：

```bash
python3 scripts/validate_artifacts.py \
  --no-recoding \
  --refseq-summary-json data/_quick/run_all/transcriptome_summary.json
```

### 版本字段约定

- `analysis_version`：分析逻辑版本（用于区分不同算法/参数版本的结果；写入数据库表的 `analysis_version` 列）
- `schema_version`：JSON 输出结构版本（仅存在于部分 summary JSON，用于回溯文件格式；在 `analysis_runs.payload` 中保留）

### 导入（psql / COPY）

1) **设置数据库连接**

从 Supabase 控制台拿到 DB URL（Postgres connection string），例如设置：

```bash
export DB_URL='postgresql://...'
```

2) **导入 recoding_sites**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.recoding_sites(
  analysis_version,k,version,definition,organism,domain,gene,product,
  cds_location,cds_start,cds_end,cds_strand,translation_start,
  aa,pos_start,pos_end,codon_dna,codon_rna,
  plus4_nt,after_codon1,after_nt6,
  n,w,v,delta,is_boundary,
  before_mean_delta,after_mean_delta,
  terminal_stop,terminal_before_mean_delta,terminal_after_mean_delta,
  control_same_codon_before_mean_delta,control_same_codon_after_mean_delta,
  control_random_cds_before_mean_delta,control_random_cds_after_mean_delta,
  before_seq_dna,after_seq_dna,
  before_gc,after_gc,before_cpg,after_cpg,before_ta,after_ta,before_dinuc,after_dinuc,
  terminal_before_gc,terminal_after_gc,terminal_before_cpg,terminal_after_cpg,terminal_before_ta,terminal_after_ta,
  terminal_before_dinuc,terminal_after_dinuc,
  nn_ctrl_before_mean_delta,nn_ctrl_after_mean_delta,nn_before_diff,nn_after_diff,nn_before_l1,nn_after_l1,
  nn_before_gc_diff,nn_after_gc_diff,nn_before_gc_eps,nn_after_gc_eps
) FROM 'data/db_exports/recoding_sites.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

3) **导入 RefSeq composition 结果**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.refseq_stop_context_comp_results(
  dataset,analysis_version,k,method,scheme,window_side,pair,
  diff,p,se,z,bins_used,n,ci_low,ci_high
) FROM 'data/db_exports/refseq_stop_context_comp_results.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

4) **导入 corpus panel items**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.corpus_panel_items(
  panel,analysis_version,dataset,code_id,label,domain,mode,present,
  records,records_with_orf,coding_tokens,boundary_token_count,boundary_rate,
  payload
) FROM 'data/db_exports/corpus_panel_items.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

5) **导入 nonstandard sequence tests items**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.nonstandard_sequence_tests_items(
  panel,analysis_version,dataset,code_id,label,domain,present,
  records_seen,records_used,records_invalid,
  start_boundary_rate,start_boundary_z,start_boundary_p,
  stop_boundary_rate,stop_boundary_z,stop_boundary_p,
  payload
) FROM 'data/db_exports/nonstandard_sequence_tests_items.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

6) **导入 boundary enrichment 结果（含 FDR $q$ 值）**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.boundary_enrichment_results(
  dataset,analysis_version,label,method,
  n_total,n_subset,boundary_rate_total,boundary_rate_subset,enrichment,p,q,
  payload
) FROM 'data/db_exports/boundary_enrichment_results.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

7) **导入跨数据集 context 汇总表（stop/start context、codon-usage null）**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.stop_context_pairwise_effects(
  panel,dataset,analysis_version,window_side,k,pair,
  n1,n2,mean1,mean2,diff,ci_low,ci_high,cohen_d,hedges_g,z,p,q,
  payload
) FROM 'data/db_exports/stop_context_pairwise_effects.csv'
WITH (FORMAT csv, HEADER true, NULL '');
\copy public.stop_context_means(
  panel,dataset,analysis_version,k,stop_codon,
  n_before,before_mean,n_after,after_mean,
  payload
) FROM 'data/db_exports/stop_context_means.csv'
WITH (FORMAT csv, HEADER true, NULL '');
\copy public.start_context_means(
  panel,dataset,analysis_version,k,start_event,
  n_before,before_mean,n_after,after_mean,
  payload
) FROM 'data/db_exports/start_context_means.csv'
WITH (FORMAT csv, HEADER true, NULL '');
\copy public.dataset_codon_usage_null(
  panel,dataset,analysis_version,
  obs_zbar,obs_ubar,
  null_mean_zbar,null_sd_zbar,
  null_mean_ubar,null_sd_ubar,
  z_zbar,z_ubar,
  p_zbar,p_ubar,
  total_codons,
  payload
) FROM 'data/db_exports/dataset_codon_usage_null.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

8) **导入 codon-usage null 分解（AA / codon 贡献）**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.codon_usage_null_decomp_aa(
  panel,dataset,analysis_version,metric,
  aa,n,obs_mean,null_mean,contrib,
  payload
) FROM 'data/db_exports/codon_usage_null_decomp_aa.csv'
WITH (FORMAT csv, HEADER true, NULL '');
\copy public.codon_usage_null_decomp_codon(
  panel,dataset,analysis_version,metric,
  codon,aa,obs_count,null_count,contrib,
  payload
) FROM 'data/db_exports/codon_usage_null_decomp_codon.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

9) **导入 recoding multi-$k$ 总体效应表**

```bash
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
\copy public.recoding_context_effects_multi_k(
  dataset,analysis_version,
  k,window_side,label,
  n1,n2,mean1,mean2,diff,ci_low,ci_high,cohen_d,hedges_g,
  p_perm,p_welch,q_welch,
  payload
) FROM 'data/db_exports/recoding_context_effects_multi_k.csv'
WITH (FORMAT csv, HEADER true, NULL '');
SQL
```

### 常用查询示例

- **查看 recoding 的分布（按 domain / codon / aa）**：

```sql
select domain, codon_rna, aa, count(*) as n
from public.recoding_sites
group by 1,2,3
order by n desc;
```

- **查看 recoding NN（within-CDS）差值分布是否整体偏移**：

```sql
select
  count(*) as n,
  avg(nn_before_diff) as mean_before_diff,
  avg(nn_after_diff) as mean_after_diff
from public.recoding_sites
where nn_before_diff is not null;
```

- **RefSeq stop-context composition 控制结果**：

```sql
select method, scheme, window_side, pair, diff, p, bins_used, n
from public.refseq_stop_context_comp_results
order by method, scheme, window_side, pair;
```

- **Corpus panel：按 domain 看 boundary rate**：

```sql
select domain, label, boundary_rate, coding_tokens
from public.corpus_panel_items
where present is true
order by domain, boundary_rate desc;
```

- **Nonstandard sequence tests：找 start/stop boundary hit 显著的样本**：

```sql
select
  panel, label, code_id,
  start_boundary_rate, start_boundary_z, start_boundary_p,
  stop_boundary_rate, stop_boundary_z, stop_boundary_p
from public.nonstandard_sequence_tests_items
where present is true
order by abs(stop_boundary_z) desc nulls last;
```

- **Boundary enrichment：按显著性排序（含 FDR $q$）**：

```sql
select dataset, label, n_subset, boundary_rate_subset, boundary_rate_total, enrichment, p, q
from public.boundary_enrichment_results
order by q asc nulls last, p asc nulls last;
```

- **RefSeq codon-usage null 分解（按贡献排序）**：

```sql
select metric, aa, n, obs_mean, null_mean, contrib
from public.codon_usage_null_decomp_aa
where dataset = 'human_refseq_mrna'
order by metric, abs(contrib) desc nulls last;
```

```sql
select metric, codon, aa, obs_count, null_count, contrib
from public.codon_usage_null_decomp_codon
where dataset = 'human_refseq_mrna'
order by metric, abs(contrib) desc nulls last;
```

- **Recoding multi-$k$ 总体效应（Welch + BH $q$）**：

```sql
select label, window_side, k, diff, ci_low, ci_high, hedges_g, p_welch, q_welch
from public.recoding_context_effects_multi_k
where dataset = 'ncbi_recoding_genbank'
order by label, window_side, k;
```

- **跨数据集 stop-context 效应（panel 内，含 BH $q$）**：

```sql
select
  panel, dataset, window_side, k, pair,
  diff, ci_low, ci_high, hedges_g, p, q
from public.stop_context_pairwise_effects
where panel = 'corpus_panel_v1' and k = 10
order by q asc nulls last, abs(diff) desc nulls last;
```

- **跨数据集 start-context 均值（panel 内）**：

```sql
select
  panel, dataset, start_event, k,
  n_before, before_mean, n_after, after_mean
from public.start_context_means
where panel = 'corpus_panel_v1' and k = 10
order by dataset, start_event;
```

- **跨数据集 codon-usage null（panel 内）**：

```sql
select
  panel, dataset, total_codons,
  obs_zbar, null_mean_zbar, z_zbar, p_zbar,
  obs_ubar, null_mean_ubar, z_ubar, p_ubar
from public.dataset_codon_usage_null
where panel = 'corpus_panel_v1'
order by p_ubar asc nulls last, abs(z_ubar) desc nulls last;
```

### 湿实验回灌（readthrough / Sec / Pyl）

本项目提供了两张表用于回灌实验数据并与预测特征联结分析：

- `public.assay_constructs`：构建体定义（序列窗口 + 预测特征），用 `construct_key` 做幂等 upsert。
- `public.assay_measurements`：实验读数（可记录 batch/replicate），用 `(construct_key, batch, replicate, measurement_type)` 做幂等 upsert。

建议实践：

- 生成 readthrough 构建体库（从 RefSeq stop-context candidates）：

```bash
python3 scripts/exp_assay_construct_library.py \
  --in-jsonl data/refseq_hsapiens_mrna/stop_context_candidates.jsonl \
  --candidate-set reporter_v1 \
  --group-labels matched_after_high,matched_after_low \
  --k 10 \
  --max-per-stop 10 \
  --out-jsonl data/assays/readthrough_constructs.jsonl \
  --out-summary-json data/assays/readthrough_constructs_summary.json
```

- 将构建体库导入 Supabase（REST）：

```bash
python3 scripts/import_supabase_rest.py \
  --assay-constructs-jsonl data/assays/readthrough_constructs.jsonl
```

- 将实验读数回灌（你可自建 `data/assays/readthrough_measurements.jsonl`，每行一条测量记录，至少包含 `construct_key` 与 `measurement_type`）：

```bash
python3 scripts/import_supabase_rest.py \
  --assay-measurements-jsonl data/assays/readthrough_measurements.jsonl
```

- 以 `refseq_stop_context_candidates` 或 `recoding_sites` 的窗口序列为来源，生成 `assay_constructs` 行（含 `k`、预测的 $\overline{U}_{\mathrm{before}}/\overline{U}_{\mathrm{after}}$、GC/dinuc 特征等）。
- 将 readthrough fraction / 插入效率等结果写入 `assay_measurements`，后续用 SQL 直接做分层对照、回归、效应量与多重检验，并通过 `scripts/exp_supabase_sql_fragments.py` 自动生成 `.tex` 片段。


