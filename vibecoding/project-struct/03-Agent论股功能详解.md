# Agent 论股功能详解

> 核心文件: `src/agent/executor.py` - AgentExecutor 类

---

## 一、功能概述

Agent 论股是基于 ReAct (Reasoning + Acting) 模式的多轮对话系统，支持用户通过自然语言与系统进行策略问答。

### 1.1 核心特性

- **多轮对话**: 支持上下文记忆的连续对话
- **工具调用**: 11+ 种数据获取和分析工具
- **策略支持**: 内置均线金叉、缠论、波浪理论等策略
- **分阶段执行**: 严格按阶段顺序获取数据和分析
- **决策仪表盘**: 输出结构化的 JSON 决策报告

### 1.2 访问方式

1. **Web 界面**: `/chat` 页面
2. **Bot 命令**: `/chat <问题>`
3. **API 接口**: `POST /api/v1/agent/chat`

---

## 二、架构设计

### 2.1 核心组件

```
AgentExecutor (executor.py)
    ├─ LLMToolAdapter (llm_adapter.py)      # LLM 工具调用适配
    ├─ ToolRegistry (tools/registry.py)     # 工具注册表
    ├─ ConversationManager (conversation.py) # 会话管理
    └─ Tools (tools/*.py)                   # 具体工具实现
```

### 2.2 工具分类

| 类别 | 工具 | 功能 |
|------|------|------|
| **行情数据** | get_realtime_quote | 获取实时行情 |
| | get_daily_history | 获取历史K线 |
| **技术分析** | analyze_trend | 技术指标分析 |
| | analyze_pattern | K线形态识别 |
| | calculate_ma | 均线计算 |
| | get_volume_analysis | 量能分析 |
| **筹码分析** | get_chip_distribution | 筹码分布分析 |
| **情报搜索** | search_stock_news | 新闻搜索 |
| | search_comprehensive_intel | 综合情报搜索 |
| **市场概览** | get_market_indices | 市场概览获取 |
| | get_sector_rankings | 行业板块分析 |
| **历史数据** | get_analysis_context | 历史分析上下文 |
| | get_stock_info | 基本信息获取 |

---

## 三、工作流程

### 3.1 系统提示词（AGENT_SYSTEM_PROMPT）

```
你是一位专注于趋势交易的 A 股投资分析 Agent，拥有数据工具和交易策略，
负责生成专业的【决策仪表盘】分析报告。

## 工作流程（必须严格按阶段顺序执行）

**第一阶段 · 行情与K线**（首先执行）
- get_realtime_quote 获取实时行情
- get_daily_history 获取历史K线

**第二阶段 · 技术与筹码**（等第一阶段结果返回后执行）
- analyze_trend 获取技术指标
- get_chip_distribution 获取筹码分布

**第三阶段 · 情报搜索**（等前两阶段完成后执行）
- search_stock_news 搜索最新资讯、减持、业绩预告等风险信号

**第四阶段 · 生成报告**（所有数据就绪后，输出完整决策仪表盘 JSON）

⚠️ 每阶段的工具调用必须完整返回结果后，才能进入下一阶段。
禁止将不同阶段的工具合并到同一次调用中。
```

### 3.2 核心交易理念

#### 1. 严进策略（不追高）
- **绝对不追高**: 乖离率 > 5% 时坚决不买入
- 乖离率 < 2%: 最佳买点区间
- 乖离率 2-5%: 可小仓介入
- 乖离率 > 5%: 严禁追高，直接判定为"观望"

#### 2. 趋势交易（顺势而为）
- **多头排列必须条件**: MA5 > MA10 > MA20
- 只做多头排列的股票，空头排列坚决不碰
- 均线发散上行优于均线粘合

#### 3. 效率优先（筹码结构）
- 关注筹码集中度: 90%集中度 < 15% 表示筹码集中
- 获利比例分析: 70-90% 获利盘时需警惕获利回吐
- 平均成本与现价关系: 现价高于平均成本 5-15% 为健康

#### 4. 买点偏好（回踩支撑）
- **最佳买点**: 缩量回踩 MA5 获得支撑
- **次优买点**: 回踩 MA10 获得支撑
- **观望情况**: 跌破 MA20 时观望

#### 5. 风险排查重点
- 减持公告、业绩预亏、监管处罚、行业政策利空、大额解禁

---

## 四、ReAct 循环执行

### 4.1 执行流程

```python
def run(self, message: str, session_id: Optional[str] = None) -> AgentResult:
    """
    Run the agent with a user message.

    ReAct loop:
    1. Build system prompt (persona + tools + skills)
    2. Send to LLM with tool declarations
    3. If tool_call → execute tool → feed result back
    4. If text → parse as final answer
    5. Loop until final answer or max_steps
    """
```

### 4.2 循环步骤

```
用户消息
    ↓
[Step 1] 构建消息历史
    ├─ 加载会话历史（如果有 session_id）
    └─ 添加用户消息
    ↓
[Step 2] 调用 LLM
    ├─ 发送系统提示词 + 工具声明 + 消息历史
    └─ 获取响应
    ↓
[Step 3] 响应处理
    ├─ 工具调用？
    │   ├─ YES → 执行工具
    │   │   ├─ 记录工具调用日志
    │   │   ├─ 生成"思考中"消息
    │   │   └─ 将工具结果添加到消息历史
    │   └─ 返回 Step 2（继续循环）
    │
    └─ 文本响应？
        ├─ YES → 解析为最终答案
        │   ├─ 尝试提取 JSON 决策仪表盘
        │   └─ 保存到会话历史
        └─ 返回 AgentResult
    ↓
[Step 4] 达到最大步数？
    ├─ YES → 返回错误
    └─ NO → 继续循环
```

### 4.3 工具执行示例

```python
# Step 1: 用户询问
user: "分析一下茅台现在适合买入吗？"

# Step 2: Agent 决定调用工具
tool_calls: [
    {"name": "get_realtime_quote", "arguments": {"code": "600519"}},
    {"name": "get_daily_history", "arguments": {"code": "600519", "days": 60}}
]

# Step 3: 执行工具并返回结果
tool_results: [
    {"price": 1650.00, "change_pct": 2.5, "volume_ratio": 1.2, ...},
    {"data": [...], "ma5": 1620.00, "ma10": 1600.00, ...}
]

# Step 4: Agent 继续调用下一阶段工具
tool_calls: [
    {"name": "analyze_trend", "arguments": {"code": "600519"}},
    {"name": "get_chip_distribution", "arguments": {"code": "600519"}}
]

# Step 5: 所有数据就绪，生成决策仪表盘
final_answer: {
    "stock_name": "贵州茅台",
    "sentiment_score": 75,
    "trend_prediction": "看多",
    "operation_advice": "持有",
    ...
}
```

---

## 五、决策仪表盘格式

### 5.1 JSON 结构

```json
{
    "stock_name": "股票中文名称",
    "sentiment_score": 0-100整数,
    "trend_prediction": "强烈看多/看多/震荡/看空/强烈看空",
    "operation_advice": "买入/加仓/持有/减仓/卖出/观望",
    "decision_type": "buy/hold/sell",
    "confidence_level": "高/中/低",
    "dashboard": {
        "core_conclusion": {
            "one_sentence": "一句话核心结论（30字以内）",
            "signal_type": "🟢买入信号/🟡持有观望/🔴卖出信号/⚠️风险警告",
            "time_sensitivity": "立即行动/今日内/本周内/不急",
            "position_advice": {
                "no_position": "空仓者建议",
                "has_position": "持仓者建议"
            }
        },
        "price_targets": {
            "entry_price": "买入价（具体数字或区间）",
            "stop_loss": "止损价",
            "take_profit": "目标价"
        },
        "technical_snapshot": {
            "trend_status": "多头排列/空头排列/震荡",
            "ma_alignment": "MA5/MA10/MA20 位置关系",
            "deviation_rate": "乖离率百分比",
            "volume_analysis": "量能分析",
            "support_resistance": "支撑位和压力位"
        },
        "chip_analysis": {
            "profit_ratio": "获利比例",
            "concentration": "筹码集中度",
            "avg_cost": "平均成本",
            "interpretation": "筹码结构解读"
        },
        "news_intel": {
            "latest_news": "最新消息摘要",
            "risk_signals": "风险信号列表",
            "sentiment": "舆情倾向"
        },
        "action_checklist": [
            {
                "item": "检查项",
                "status": "✅满足 / ⚠️注意 / ❌不满足",
                "detail": "详细说明"
            }
        ],
        "risk_warnings": ["风险提示1", "风险提示2"],
        "strategy_match": {
            "activated_strategies": ["策略名称"],
            "strategy_signals": "策略信号说明"
        }
    }
}
```

### 5.2 关键字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| sentiment_score | 情绪评分 (0-100) | 75 |
| trend_prediction | 趋势预测 | "看多" |
| operation_advice | 操作建议 | "持有" |
| decision_type | 决策类型 | "hold" |
| confidence_level | 置信度 | "高" |
| entry_price | 买入价 | "1620-1630元" |
| stop_loss | 止损价 | "1580元" |
| take_profit | 目标价 | "1720元" |

---

## 六、会话管理

### 6.1 ConversationManager

```python
class ConversationManager:
    """Manages multiple conversation sessions with TTL."""

    def __init__(self, ttl_minutes: int = 30):
        self._sessions: Dict[str, ConversationSession] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get_or_create(self, session_id: str) -> ConversationSession:
        """Get an existing session or create a new one."""
        self._cleanup_expired()

        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id)

        return self._sessions[session_id]
```

### 6.2 会话特性

- **TTL**: 30 分钟无活动自动过期
- **持久化**: 消息历史存储到数据库
- **上下文**: 支持多轮对话上下文记忆
- **清理**: 自动清理过期会话

---

## 七、集成方式

### 7.1 Web 界面 (ChatPage.tsx)

```typescript
// 发送消息
const handleSend = async () => {
    const response = await agentApi.chat(input, sessionId);
    setMessages([...messages, userMsg, assistantMsg]);
};

// 渲染决策仪表盘
{message.dashboard && (
    <DashboardView dashboard={message.dashboard} />
)}
```

### 7.2 Bot 命令 (/chat)

```python
def execute(self, message: BotMessage, args: list[str]) -> BotResponse:
    user_message = " ".join(args)
    session_id = f"{message.platform}_{message.user_id}"

    from src.agent.factory import build_agent_executor
    executor = build_agent_executor(config)
    result = executor.chat(message=user_message, session_id=session_id)

    if result.success:
        return BotResponse.text_response(result.content)
```

### 7.3 API 接口

```python
@router.post("/chat")
async def agent_chat(request: AgentChatRequest):
    executor = build_agent_executor(get_config())
    result = executor.chat(
        message=request.message,
        session_id=request.session_id
    )

    return AgentChatResponse(
        success=result.success,
        content=result.content,
        dashboard=result.dashboard,
        session_id=request.session_id
    )
```

---

## 八、策略系统

### 8.1 内置策略

Agent 支持 11 种内置策略，通过配置 `agent_skills` 激活：

1. **均线金叉**: MA5 上穿 MA10
2. **缠论**: 缠论笔、段、中枢分析
3. **波浪理论**: 艾略特波浪识别
4. **MACD**: MACD 金叉死叉
5. **KDJ**: KDJ 超买超卖
6. **布林带**: 布林带突破
7. **成交量**: 量价配合分析
8. **筹码分布**: 筹码集中度分析
9. **趋势跟踪**: 趋势强度判断
10. **支撑压力**: 关键价位识别
11. **形态识别**: K线形态识别

### 8.2 策略配置

```python
# 配置文件或环境变量
AGENT_SKILLS = ["均线金叉", "MACD", "成交量"]

# 或使用 "all" 激活所有策略
AGENT_SKILLS = ["all"]
```

---

## 九、错误处理

### 9.1 工具失败处理

```python
# 规则: 记录失败原因，使用已有数据继续分析，不重复调用失败工具

if tool_result.get("error"):
    logger.warning(f"Tool {tool_name} failed: {tool_result['error']}")
    # 继续使用其他工具的数据
    continue
```

### 9.2 最大步数限制

```python
# 默认最大步数: 10
if self.total_steps >= self.max_steps:
    return AgentResult(
        success=False,
        error=f"Reached max steps ({self.max_steps})"
    )
```

### 9.3 JSON 解析容错

```python
# 使用 json_repair 库修复不完整的 JSON
try:
    dashboard = json.loads(content)
except:
    repaired = repair_json(content)
    dashboard = json.loads(repaired)
```

---

## 十、性能优化

### 10.1 并发工具调用

```python
# 同一阶段的工具可以并发执行
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(tool_func, **args)
        for tool_func, args in tool_calls
    ]
    results = [f.result() for f in as_completed(futures)]
```

### 10.2 缓存机制

- **实时行情**: 缓存 1 分钟
- **历史K线**: 缓存当日
- **筹码分布**: 缓存 5 分钟

### 10.3 Token 使用统计

```python
# 记录每次 LLM 调用的 token 使用
self.total_tokens += response.usage.total_tokens

# 持久化到数据库
persist_llm_usage(
    provider=self.provider,
    model=self.model,
    total_tokens=self.total_tokens,
    call_type="agent_chat"
)
```

---

## 十一、调试与监控

### 11.1 工具调用日志

```python
tool_calls_log = [
    {
        "step": 1,
        "tool": "get_realtime_quote",
        "arguments": {"code": "600519"},
        "result": {...},
        "duration_ms": 150
    },
    ...
]
```

### 11.2 思考过程展示

```python
# 生成"思考中"消息
thinking_msg = f"🤔 正在{tool_label}..."

# 前端实时展示
yield {"type": "thinking", "content": thinking_msg}
```

---

## 十二、最佳实践

### 12.1 用户提问建议

- **明确股票**: "分析 600519" 优于 "分析茅台"
- **具体问题**: "现在适合买入吗？" 优于 "怎么样？"
- **策略指定**: "用均线金叉策略分析" 可激活特定策略

### 12.2 系统配置建议

- **Agent 模式**: 交互式问答场景启用
- **传统模式**: 批量分析场景使用
- **混合模式**: 根据 `agent_skills` 自动切换

---

## 十三、未来扩展

### 13.1 计划功能

- [ ] 支持更多策略（如海龟交易法、网格交易）
- [ ] 多股票对比分析
- [ ] 历史回测集成
- [ ] 实时行情推送
- [ ] 语音交互支持

### 13.2 优化方向

- [ ] 工具调用并发优化
- [ ] 缓存策略优化
- [ ] Token 使用优化
- [ ] 响应速度优化
