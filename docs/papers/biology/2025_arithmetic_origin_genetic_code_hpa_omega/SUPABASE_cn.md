### Supabase 数据库（Postgres）搭建与导入

本项目提供了可直接用于 Supabase 的 schema migration，以及把实验输出导出为 CSV 的脚本，便于在 Postgres 里做可查询、可复现的统计分析。

### 目录

- **schema/migration**：`supabase/migrations/`（按时间顺序执行）
- **导出脚本**：`scripts/export_supabase_tables.py`

### 本地 Supabase（推荐）

- **启动**：
  - 进入目录：`docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega`
  - 运行 `supabase start`
  - 运行 `supabase db reset`（会自动应用 `supabase/migrations/`）
  - 用 `supabase status` 查看 DB 连接串

### 云端 Supabase

- **创建项目**：在 Supabase 控制台创建项目（Postgres）
- **应用 migration**：用 Supabase SQL Editor 按顺序执行 `supabase/migrations/*.sql`（或用 psql 连接后依次执行这些文件）

### Python 直连导入（PostgREST / REST，无需 psql）

本仓库提供了一个**纯标准库**的导入脚本，直接走 Supabase 的 PostgREST 接口写入五张表（含 provenance 的 `analysis_runs`）。

1) **准备连接信息文件（git ignore）**

- 复制模板：`supabase.env.template` → `supabase.env`
- 填写：
  - `SUPABASE_URL`
  - `SUPABASE_KEY`（建议使用可写入数据库的 key）
  - `DATABASE_URL`（可选，仅用于你自己用 psql/驱动直连时）

2) **执行导入**

在项目根目录 `docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega` 下运行：

```bash
python3 scripts/import_supabase_rest.py --batch-size 200
```

如果你的 Python 环境遇到证书链问题，可临时加 `--insecure`（仅用于本机证书缺失的场景）：

```bash
python3 scripts/import_supabase_rest.py --batch-size 200 --insecure
```

3) **可选：指定输入文件（支持 quick 产物）**

默认使用：

- `data/recoding_genbank/recoding_sites.jsonl`
- `data/recoding_genbank/recoding_sites_summary.json`
- `data/refseq_hsapiens_mrna/transcriptome_summary.json`
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
- `data/db_exports/corpus_panel_items.csv`
- `data/db_exports/nonstandard_sequence_tests_items.csv`

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

从 `supabase status` 或 Supabase 控制台拿到 DB URL，例如设置：

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


