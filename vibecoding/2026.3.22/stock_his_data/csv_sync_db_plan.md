# CSV 同步 PostgreSQL 方案

## 结论

建议采用这条主线：

`CSV 扫描 -> 表头识别 -> 字段标准化 -> staging 批量导入 -> stock_daily upsert -> MA 回填 -> 校验`

不建议直接复用当前仓库里逐行 ORM upsert 的写法做这次历史全量导入。

## 已确认事实

### 数据范围

- 源目录：`E:\learning\stock\stock\增量\日线`
- 目录按年份分区，当前存在 `1990` 到 `2026`
- 本次需求范围应按年份过滤为 `2000+`
- 当前磁盘上最新文件是 `2026-03-19.csv`

说明：
需求说明写的是到 `2026-03-20`，但当前实际文件系统扫描到的最后一天是 `2026-03-19`。导入方案里需要把这个差异写清楚，避免后续核对时误判。

### CSV 格式并非完全一致

历史大多数文件使用旧表头：

```csv
序号,代码,名称,日期,昨收,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅
```

从 `2026-01-12.csv` 开始，出现了新表头版本：

```csv
日期,代码,名称,昨收,开盘,最高,最低,收盘,成交量(股),成交额(元),涨跌(元),涨跌幅(%),换手率(%),流通股本(股),总股本(股)
```

已扫描到的统计结果：

- 旧表头文件数：`8563`
- 新表头文件数：`51`

这意味着导入器必须按“表头名”识别字段，不能按列位置硬编码。

### 仓库现状

- [storage.py](E:\work\python_ws\daily_stock_analysis\src\storage.py:63) 已有 `stock_daily` 模型
- [config.py](E:\work\python_ws\daily_stock_analysis\src\config.py:1263) 已支持 PostgreSQL 连接串
- [requirements.txt](E:\work\python_ws\daily_stock_analysis\requirements.txt:49) 已包含 `psycopg[binary]`
- 当前 [storage.py](E:\work\python_ws\daily_stock_analysis\src\storage.py:1014) 的写库路径是逐行 ORM 查询后更新/插入

结论：
应用日常写入可以继续用 ORM，但历史批量回灌不适合这条路径。

## 字段映射建议

### 可直接映射到 `stock_daily`

| 目标字段 | 旧表头来源 | 新表头来源 |
|------|------|------|
| `code` | `代码` | `代码` |
| `bane` | `名称` | `名称` |
| `date` | `日期` | `日期` |
| `open` | `开盘` | `开盘` |
| `high` | `最高` | `最高` |
| `low` | `最低` | `最低` |
| `close` | `收盘` | `收盘` |
| `volume` | `成交量` | `成交量(股)` |
| `amount` | `成交额` | `成交额(元)` |
| `pct_chg` | `涨跌幅` | `涨跌幅(%)` |
| `data_source` | 常量填充 | 常量填充 |
| `created_at` | `now()` | `now()` |
| `updated_at` | `now()` | `now()` |

### 建议第一版忽略的源字段

- `序号`
- `名称`
- `昨收`
- `振幅`
- `涨跌(元)`
- `换手率(%)`
- `流通股本(股)`
- `总股本(股)`

如果后续确实有业务价值，可以先进 staging，不建议第一版先改主表。

### 目标表中无法直接从源 CSV 获得的字段

| 目标字段 | 建议 |
|------|------|
| `ma5` | 导入后回填 |
| `ma10` | 导入后回填 |
| `ma20` | 导入后回填 |
| `volume_ratio` | 第一版先置 `NULL` |

说明：
源 CSV 没有直接提供 `ma5`、`ma10`、`ma20`、`volume_ratio`。其中均线可以按导入后的历史数据补算，`volume_ratio` 则需要确认具体公式后再补，第一版不建议猜。

## 股票代码标准化建议

源数据里的代码形态类似：

- `sh600000`
- `sz000001`

仓库现有标准化逻辑会把它们转成纯数字代码：

- `sh600000 -> 600000`
- `sz000001 -> 000001`

参考：
[stock_code_utils.py](E:\work\python_ws\daily_stock_analysis\src\services\stock_code_utils.py:52)

建议：
导入到 `stock_daily.code` 时直接存标准化后的纯数字代码，以保持与当前仓库查询和分析逻辑一致。

## 推荐执行流程

### 1. 建 staging 表和导入清单表

建议新增：

- `stock_daily_stage`
- `stock_daily_import_manifest`

其中：

- `stock_daily_stage` 用于承接标准化后的原始 CSV 数据
- `stock_daily_import_manifest` 用于记录文件级导入状态，支持断点续跑和失败重试

### 2. 实现专用导入脚本

建议新增脚本：

- `scripts/import_stock_daily_csv.py`

脚本职责：

1. 扫描 `E:\learning\stock\stock\增量\日线`
2. 只处理 `2000` 到 `2026` 年目录
3. 读取首行识别旧表头或新表头
4. 映射为统一字段结构
5. 标准化 `code`
6. 分批导入 staging
7. 更新 manifest

### 3. 从 staging 合并到正式表

建议使用 PostgreSQL 的 `ON CONFLICT (code, date) DO UPDATE`：

```sql
INSERT INTO stock_daily (...)
SELECT ...
FROM stock_daily_stage
ON CONFLICT (code, date) DO UPDATE
SET ...
```

这样做的好处是：

- 可重复执行
- 不会生成重复记录
- 后续增量补文件时可以复用同一条链路

### 4. 回填均线指标

导入完原始日线后，再按 `code` 分组、按 `date` 排序回填：

- `ma5`
- `ma10`
- `ma20`

建议直接用 SQL 窗口函数处理，逻辑更清晰，也方便重复执行。

`volume_ratio` 第一版先留空。

### 5. 校验导入结果

至少做以下校验：

1. manifest 成功文件数与源文件数是否一致
2. 按年份统计的源行数与落库行数是否一致
3. `stock_daily` 中 `(code, date)` 是否仍然唯一
4. 最小日期与最大日期是否符合预期
5. 抽样若干 CSV，逐行核对关键字段

## 为什么不建议直接用当前 ORM 路径

当前 [storage.py](E:\work\python_ws\daily_stock_analysis\src\storage.py:1014) 的逻辑本质上是：

1. 每行先查是否存在
2. 存在则更新
3. 不存在则插入

这条路径的问题是：

- 对全量历史数据太慢
- 每行都有数据库往返
- 失败后恢复粒度较粗
- 不适合 8000+ 文件的历史回灌

更稳妥的方案是：

`COPY 到 staging + SQL merge`

## 风险点

### 数据截止日期不一致

- 需求描述：到 `2026-03-20`
- 当前实际文件：到 `2026-03-19`

### CSV 后续可能继续变更表头

导入器需要对未知表头直接报错并记入 manifest，不能静默吞掉。

### `volume_ratio` 含义未确认

如果业务没有给出明确公式，第一版就不要写死。

### 代码格式必须统一

不要在目标表里混入：

- `600000`
- `sh600000`
- `000001.SZ`

第一版就统一格式，后面查询最省事。

## 建议拆分的实施任务

1. 先冻结字段映射、表头识别、代码标准化规则
2. 再实现 staging 与 manifest
3. 再实现 CSV 扫描和批量导入脚本
4. 再实现 `stock_daily` merge
5. 最后补均线回填和校验 runbook

## 对应的 lite-plan 会话

这次 `workflow-lite-plan` 的计划会话已经落在下面这些文件里：

- [context.md](E:\work\python_ws\daily_stock_analysis\.workflow\.lite-plan\wpp-csv-sync-db-20260322\context.md:1)
- [tasks.csv](E:\work\python_ws\daily_stock_analysis\.workflow\.lite-plan\wpp-csv-sync-db-20260322\tasks.csv:1)
- [explore.csv](E:\work\python_ws\daily_stock_analysis\.workflow\.lite-plan\wpp-csv-sync-db-20260322\explore.csv:1)

如果你要继续下一步，我可以直接按 `T2` 和 `T3` 开始落地导入脚本和 staging SQL。
