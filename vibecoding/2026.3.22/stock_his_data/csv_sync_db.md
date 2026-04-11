1. 我现在有一批A股历史数据，包含2000年至2026.3.20 日的所有日线数据
2. 现在需要你探索一个方案，从csv文件中读取并写入到postgre数据库
3. 我提供给你一个sql-ddl ，你根据csv的内容，给出一个迁移到postgre的方案。
4. 结果汇总到同文件夹下

## 要求
1. 忽略当前项目逻辑，只根据我提供的csv文件分析迁移方案

## 参考数据:
csv: "E:\learning\stock\stock\增量\日线" 该文件夹下的文件格式相同，需要同步到postgre里面

ddl:
```
CREATE TABLE "public"."stock_daily" (
  -- 将 int4 + DEFAULT nextval 替换为 SERIAL
  "id" SERIAL PRIMARY KEY, 
  "code" varchar(20) NOT NULL,
  "name" varchar(20) NOT NULL,
  "date" date NOT NULL,
  "open" float8,
  "high" float8,
  "low" float8,
  "close" float8,
  "volume" float8,
  "amount" float8,
  "pct_chg" float8,
  "ma5" float8,
  "ma10" float8,
  "ma20" float8,
  "volume_ratio" float8,
  "data_source" varchar(50),
  "created_at" timestamp(6),
  "updated_at" timestamp(6),
  CONSTRAINT "uix_code_date" UNIQUE ("code", "date")
);

ALTER TABLE "public"."stock_daily" 
  OWNER TO "zl-postgres";

CREATE INDEX "ix_code_date" ON "public"."stock_daily" USING btree (
  "code" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);

CREATE INDEX "ix_stock_daily_code" ON "public"."stock_daily" USING btree (
  "code" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

CREATE INDEX "ix_stock_daily_date" ON "public"."stock_daily" USING btree (
  "date" "pg_catalog"."date_ops" ASC NULLS LAST
);

COMMENT ON COLUMN "public"."stock_daily"."id" IS '自增主键 ID';

COMMENT ON COLUMN "public"."stock_daily"."code" IS '股票代码 (如: sh.600000 或 000001.SZ)';

COMMENT ON COLUMN "public"."stock_daily"."date" IS '行情日期';

COMMENT ON COLUMN "public"."stock_daily"."open" IS '开盘价';

COMMENT ON COLUMN "public"."stock_daily"."high" IS '最高价';

COMMENT ON COLUMN "public"."stock_daily"."low" IS '最低价';

COMMENT ON COLUMN "public"."stock_daily"."close" IS '收盘价';

COMMENT ON COLUMN "public"."stock_daily"."volume" IS '成交量 (手/股，视数据源而定)';

COMMENT ON COLUMN "public"."stock_daily"."amount" IS '成交额';

COMMENT ON COLUMN "public"."stock_daily"."pct_chg" IS '涨跌幅 (百分比)';

COMMENT ON COLUMN "public"."stock_daily"."ma5" IS '5日移动平均线';

COMMENT ON COLUMN "public"."stock_daily"."ma10" IS '10日移动平均线';

COMMENT ON COLUMN "public"."stock_daily"."ma20" IS '20日移动平均线';

COMMENT ON COLUMN "public"."stock_daily"."volume_ratio" IS '量比';

COMMENT ON COLUMN "public"."stock_daily"."data_source" IS '数据来源 (如: tushare, baostock, akshare)';

COMMENT ON COLUMN "public"."stock_daily"."created_at" IS '记录创建时间';

COMMENT ON COLUMN "public"."stock_daily"."updated_at" IS '记录最后更新时间';

COMMENT ON TABLE "public"."stock_daily" IS '股票日线行情数据表，存储每日开盘、收盘、成交量及常用均线指标';
```