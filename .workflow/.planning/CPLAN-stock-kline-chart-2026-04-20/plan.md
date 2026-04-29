# 执行计划：个股看盘 K线图功能

**Session**: CPLAN-stock-kline-chart-2026-04-20
**Created**: 2026-04-20
**Estimated Time**: ~150 minutes (后端) + ~150 分钟 (前端)

---

## 需求概述

在 StrategyBacktestPage.tsx 页面增加"个股看盘"功能：用户输入股票代码后，展示类似同花顺的K线图界面，支持日K/周K/月K、成交量、MACD/KDJ/BOLL指标。

**技术选型**: KLineChart (~40KB, MIT, 内置指标, 支持画线)

---

## 子域拆分

| 子域 | 描述 | 任务ID范围 |
|------|------|-----------|
| Backend API | K线数据查询、周期聚合、指标计算、筹码分布 | TASK-001 ~ TASK-005 |
| Frontend Chart | KLineChart集成、React组件封装、页面整合 | TASK-101 ~ TASK-105 |

---

## 执行计划

### Phase A: Backend API (先执行)

| 任务 | 描述 | 复杂度 | 依赖 | 估计时间 |
|------|------|--------|------|---------|
| TASK-001 | Pydantic schemas: KlineBar, KlineDataResponse, ChipDistributionResponse | Low | 无 | 15min |
| TASK-002 | KlineService: 日/周/月K聚合 + MACD/KDJ/BOLL指标计算 | Medium | 无 | 40min |
| TASK-003 | GET `/api/v1/kline/{code}` 端点 | Low | 001, 002 | 20min |
| TASK-004 | GET `/api/v1/kline/{code}/chip-distribution` 端点 | Low | 001, 003 | 15min |
| TASK-005 | Router注册 + 集成验证 | Low | 003, 004 | 10min |

**并行机会**: TASK-001 和 TASK-002 可并行执行

### Phase B: Frontend Chart (依赖 Backend 完成)

| 任务 | 描述 | 复杂度 | 依赖 | 估计时间 |
|------|------|--------|------|---------|
| TASK-101 | 安装 klinecharts + 类型定义 `stockChart.ts` | Low | 无 | 15min |
| TASK-102 | API层 `stockChart.ts` (GET /api/v1/kline/{code}) | Low | 101 | 15min |
| TASK-103 | KLineChart React 封装组件 | Medium | 101 | 40min |
| TASK-104 | StockChartPanel (周期选择 + 指标切换) | Medium | 102, 103 | 40min |
| TASK-105 | 集成到 StrategyBacktestPage Tab | Medium | 104 | 30min |

**并行机会**: TASK-102 和 TASK-103 可并行执行

---

## 文件变更清单

### 新增文件
| 文件 | 任务 |
|------|------|
| `api/v1/schemas/kline.py` | TASK-001 |
| `src/services/kline_service.py` | TASK-002 |
| `api/v1/endpoints/kline.py` | TASK-003, TASK-004 |
| `apps/dsa-web/src/types/stockChart.ts` | TASK-101 |
| `apps/dsa-web/src/api/stockChart.ts` | TASK-102 |
| `apps/dsa-web/src/components/stock-chart/KLineChart.tsx` | TASK-103 |
| `apps/dsa-web/src/components/stock-chart/StockChartPanel.tsx` | TASK-104 |
| `apps/dsa-web/src/components/stock-chart/index.ts` | TASK-103, TASK-104 |

### 修改文件
| 文件 | 任务 | 修改内容 |
|------|------|---------|
| `api/v1/router.py` | TASK-005 | 添加 kline 路由注册 |
| `apps/dsa-web/package.json` | TASK-101 | 添加 klinecharts 依赖 |
| `apps/dsa-web/src/pages/StrategyBacktestPage.tsx` | TASK-105 | 右侧面板添加 Tab 切换 |

---

## 冲突报告

1个已解决冲突:
- **API路径对齐**: 统一使用 `/api/v1/kline/{code}` (前端TASK-102已修正)

无文件级冲突 - Backend 和 Frontend 修改完全独立的文件集。

---

## 执行建议

使用 Codex 按以下顺序执行:

1. **Backend**: TASK-001 + TASK-002 (并行) -> TASK-003 -> TASK-004 -> TASK-005
2. **Frontend**: TASK-101 -> TASK-102 + TASK-103 (并行) -> TASK-104 -> TASK-105
3. **集成测试**: 端到端验证 K线图显示

总计 10 个任务，预计 2-3 小时完成。
