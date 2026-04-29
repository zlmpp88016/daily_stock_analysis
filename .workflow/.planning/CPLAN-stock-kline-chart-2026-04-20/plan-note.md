---
session_id: CPLAN-stock-kline-chart-2026-04-20
original_requirement: StrategyBacktestPage.tsx 增加个股看盘功能：输入股票代码，回显日K/周K/月K、筹码、成交量、MACD/KDJ/BOLL指标，类似同花顺
created_at: 2026-04-20
contributors: [understanding-agent]
sub_domains:
  - focus_area: backend-api
    description: 后端API - 提供K线数据、技术指标计算、筹码分布接口
    task_id_range: [1, 100]
  - focus_area: frontend-chart
    description: 前端图表 - KLineChart集成、K线组件、指标叠加、页面整合
    task_id_range: [101, 200]
agent_sections:
  - "任务池 - Backend Api"
  - "任务池 - Frontend Chart"
agent_task_id_ranges:
  backend-api: "TASK-001 ~ TASK-100"
  frontend-chart: "TASK-101 ~ TASK-200"
status: planning
---

## 需求理解

### 核心目标
在 StrategyBacktestPage.tsx 页面增加"个股看盘"功能，用户输入股票代码后，展示类似同花顺的个股K线图界面。

### 关键点
1. **K线周期**: 日K、周K、月K三种周期切换
2. **技术指标**: MACD、KDJ、BOLL叠加显示
3. **成交量**: 主图下方显示成交量柱状图
4. **筹码分布**: 显示筹码分布数据
5. **数据来源**: 仅使用数据库 `stock_daily` 表数据，不调用外部接口
6. **图表库**: 使用 KLineChart (MIT, ~40KB, 内置指标, 支持画线)

### 约束
- 股票数据只能从 `stock_daily` 数据库表获取
- MACD/KDJ/BOLL 指标计算复用 `src/strategy_backtest/indicators.py` 中已有代码
- 周K/月K需要在后端聚合日K数据
- 筹码分布目前从外部API获取（DataFetcherManager.get_chip_distribution），需评估是否满足"仅用数据库数据"的要求
- 前端使用 React 19 + Vite + TailwindCSS + TypeScript

### 现有代码资产
- **数据库**: `stock_daily` 表存储日K OHLCV数据 + MA5/MA10/MA20
- **指标计算**: `src/strategy_backtest/indicators.py` 有 calc_macd/calc_kdj/calc_boll
- **数据仓库**: `StockRepository` 有 get_range/get_latest 方法
- **数据获取**: `DataFetcherManager` 有 get_daily_data/get_chip_distribution 方法
- **前端**: 已有 Recharts，但不适配K线图；需引入 KLineChart

### 拆分策略
按前后端分离拆分：
1. **Backend API**: 新增K线数据查询API + 指标计算 + 周期聚合
2. **Frontend Chart**: 引入KLineChart + 封装组件 + 页面整合

---

## 任务池 - Backend Api

<!-- PRE-ALLOCATED for backend-api agent: TASK-001 ~ TASK-100 -->

### TASK-001: Define K-line data and indicator Pydantic schemas [backend-api]
- **状态**: pending
- **复杂度**: Low
- **依赖**: 无
- **范围**: `api/v1/schemas/kline.py` (新建)
- **修改点**: 创建 KlineBar, KlineIndicatorBar, KlineDataResponse, ChipDistributionResponse 等 Pydantic v2 模型
- **冲突风险**: 低 - 新文件，不修改现有代码

### TASK-002: Implement K-line data service with period aggregation and indicator calculation [backend-api]
- **状态**: pending
- **复杂度**: Medium
- **依赖**: 无 (与 TASK-001 可并行)
- **范围**: `src/services/kline_service.py` (新建)
- **修改点**: 创建 KlineService，实现日/周/月K聚合 (pandas resample) + MACD/KDJ/BOLL 指标计算 (复用 indicators.py)
- **冲突风险**: 低 - 新文件，依赖已有 indicators.py 和 StockRepository

### TASK-003: Create K-line data API endpoint [backend-api]
- **状态**: pending
- **复杂度**: Low
- **依赖**: TASK-001, TASK-002
- **范围**: `api/v1/endpoints/kline.py` (新建)
- **修改点**: 创建 GET /api/v1/kline/{code} 端点，支持 period/start_date/end_date/limit 查询参数
- **冲突风险**: 低 - 新文件

### TASK-004: Create chip distribution API endpoint [backend-api]
- **状态**: pending
- **复杂度**: Low
- **依赖**: TASK-001, TASK-003
- **范围**: `api/v1/endpoints/kline.py` (追加)
- **修改点**: 在 kline.py 中添加 GET /{code}/chip-distribution 端点，调用 DataFetcherManager.get_chip_distribution()
- **冲突风险**: 低 - 与 TASK-003 同文件但不同端点

### TASK-005: Register kline router in API v1 router and verify integration [backend-api]
- **状态**: pending
- **复杂度**: Low
- **依赖**: TASK-003, TASK-004
- **范围**: `api/v1/router.py`
- **修改点**: 添加 kline 路由注册 `router.include_router(kline.router, prefix='/kline', tags=['Kline'])`
- **冲突风险**: 中 - 修改 router.py，前端 agent 不涉及此文件

---

## 任务池 - Frontend Chart

<!-- PRE-ALLOCATED for frontend-chart agent: TASK-101 ~ TASK-200 -->

### TASK-101: Install klinecharts and define stock chart type definitions [frontend-chart]
- **状态**: pending
- **复杂度**: Low
- **依赖**: 无
- **范围**: `apps/dsa-web/src/types/`, `apps/dsa-web/package.json`
- **修改点**:
  - `apps/dsa-web/package.json` - 添加 klinecharts 依赖
  - `apps/dsa-web/src/types/stockChart.ts` - 新建 K线数据类型定义
- **冲突风险**: 低（仅新增文件+修改 package.json，与 backend-api 无交叉）

### TASK-102: Create stock chart API layer with Axios client [frontend-chart]
- **状态**: pending
- **复杂度**: Low
- **依赖**: TASK-101
- **范围**: `apps/dsa-web/src/api/`
- **修改点**:
  - `apps/dsa-web/src/api/stockChart.ts` - 新建 K线数据 API 层（GET /api/v1/stock-chart/{code}）
- **冲突风险**: 低（新建文件，API 端点与 backend-api agent 规划的端点对齐）

### TASK-103: Create KLineChart React wrapper component [frontend-chart]
- **状态**: pending
- **复杂度**: Medium
- **依赖**: TASK-101
- **范围**: `apps/dsa-web/src/components/stock-chart/`
- **修改点**:
  - `apps/dsa-web/src/components/stock-chart/KLineChart.tsx` - 新建 klinecharts React 封装组件
  - `apps/dsa-web/src/components/stock-chart/index.ts` - 新建 barrel export
- **冲突风险**: 低（新建文件，无交叉依赖）

### TASK-104: Create StockChartPanel with period selector and indicator toggles [frontend-chart]
- **状态**: pending
- **复杂度**: Medium
- **依赖**: TASK-102, TASK-103
- **范围**: `apps/dsa-web/src/components/stock-chart/`
- **修改点**:
  - `apps/dsa-web/src/components/stock-chart/StockChartPanel.tsx` - 新建完整看盘面板（工具栏+图表区）
  - `apps/dsa-web/src/components/stock-chart/index.ts` - 更新导出
- **冲突风险**: 低（新建文件，消费 TASK-102 API + TASK-103 组件）

### TASK-105: Integrate StockChartPanel into StrategyBacktestPage [frontend-chart]
- **状态**: pending
- **复杂度**: Medium
- **依赖**: TASK-104
- **范围**: `apps/dsa-web/src/pages/StrategyBacktestPage.tsx`
- **修改点**:
  - `apps/dsa-web/src/pages/StrategyBacktestPage.tsx` - 在右侧面板添加 Tab 切换器（回测结果/个股看盘）
- **冲突风险**: 中（修改 StrategyBacktestPage.tsx，需确保不影响现有回测功能）

---

## 依赖关系

### Backend API 内部依赖
- TASK-001 (schemas) -> TASK-003 (endpoint)
- TASK-002 (service) -> TASK-003 (endpoint)
- TASK-003 (kline endpoint) -> TASK-004 (chip endpoint, same file)
- TASK-003 + TASK-004 -> TASK-005 (router registration)
- TASK-001 与 TASK-002 可并行执行

### Frontend Chart 内部依赖
- TASK-101 (types) -> TASK-102 (API), TASK-103 (component)
- TASK-102 + TASK-103 -> TASK-104 (panel)
- TASK-104 -> TASK-105 (page integration)

### 跨域依赖
- Frontend TASK-102 (API layer) 依赖 Backend K线端点 (TASK-003, TASK-005)
- Frontend TASK-104 (panel) 消费 Backend API 响应格式 (TASK-001 schemas)
- API 端点路径需对齐: Backend `/api/v1/kline/{code}` vs Frontend 调用路径

---

## 冲突标记

### 无文件冲突
- Backend 新文件与 Frontend 新文件无交叉
- `api/v1/router.py` 仅 TASK-005 修改
- `apps/dsa-web/src/pages/StrategyBacktestPage.tsx` 仅 TASK-105 修改

### CONFLICT-001: API 端点路径不一致 [medium]
- **严重程度**: medium
- **涉及任务**: TASK-002, TASK-003
- **涉及Agent**: backend-api, frontend-chart
- **问题详情**: Backend 规划 `/api/v1/kline/{code}`，Frontend TASK-102 引用 `/api/v1/stock-chart/{code}`
- **建议解决方案**: Frontend TASK-102 执行时使用 `/api/v1/kline/{code}` 作为 API 端点路径
- **决策状态**: [x] 已解决 - 统一使用 `/api/v1/kline/{code}`

---

## 上下文证据 - Backend Api

<!-- Evidence for backend-api agent -->

### 相关文件
- `src/storage.py` - StockDaily ORM模型 + DatabaseManager
- `src/repositories/stock_repo.py` - StockRepository 数据查询
- `src/strategy_backtest/indicators.py` - MACD/KDJ/BOLL指标计算
- `src/services/stock_service.py` - StockService 数据获取
- `data_provider/base.py` - DataFetcherManager 外部数据获取
- `data_provider/realtime_types.py` - ChipDistribution 数据模型
- `api/v1/endpoints/strategy_backtest.py` - 现有API端点参考
- `api/v1/schemas/strategy_backtest.py` - 现有Schema参考
- `api/v1/router.py` - 路由注册

### 现有模式
- API端点通过 FastAPI Router 注册
- Schema 使用 Pydantic v2 模型
- Repository 使用 SQLAlchemy ORM
- Service 层编排 Repository + 外部数据获取

### 约束
- 数据库只有日K数据，周K/月K需要聚合
- 筹码分布需从 DataFetcherManager 获取（外部API）
- 指标计算可复用 indicators.py

---

## 上下文证据 - Frontend Chart

<!-- Evidence for frontend-chart agent -->

### 相关文件
- `apps/dsa-web/package.json` - 当前依赖（react 19, recharts 3.8, axios, zustand）
- `apps/dsa-web/src/pages/StrategyBacktestPage.tsx` - 目标页面 (810行)，左右分栏布局，左侧表单右侧结果
- `apps/dsa-web/src/components/strategy-backtest/` - 现有组件目录：EquityCurve.tsx, TradeTable.tsx, RuleBuilder.tsx
- `apps/dsa-web/src/components/common/` - 公共组件：Card, Badge, Collapsible, Loading, ApiErrorAlert
- `apps/dsa-web/src/types/strategyBacktest.ts` - 类型定义参考（IndicatorConfig 已含 MACD/KDJ/BOLL 类型）
- `apps/dsa-web/src/api/strategyBacktest.ts` - API层参考（snake_case 转换 + toCamelCase 响应）
- `apps/dsa-web/src/api/index.ts` - Axios 实例（30s timeout, camelcase-keys transform）
- `apps/dsa-web/src/api/utils.ts` - toCamelCase 工具函数
- `apps/dsa-web/src/App.tsx` - 路由定义（/strategy-backtest 路由已有）

### 现有模式
- React 19 + TypeScript 5.9 + Vite 7 + TailwindCSS 4
- 组件按功能分目录：`src/components/{feature}/` + `index.ts` barrel export
- API 层：`src/api/{feature}.ts`，使用 apiClient + toCamelCase，请求参数 snake_case 转换
- 类型定义：`src/types/{feature}.ts`，interface 导出
- 页面状态管理：useState 管理 form/loading/error/data，async fetch + try/catch
- 样式：terminal-card, gradient-border-card, btn-primary, input-terminal, label-uppercase 等

### 约束
- klinecharts 框架无关，需 React 封装（useRef + useEffect 生命周期管理）
- API 端点与 backend-api agent 规划对齐：GET /api/v1/kline/{code}?period=X&start_date=Y&end_date=Z
- 响应数据经 camelcase-keys 转换后使用
- 新增文件不修改现有文件（仅 StrategyBacktestPage.tsx 需修改以集成 Tab）
- 股票代码从现有表单字段 form.code 同步到图表组件
