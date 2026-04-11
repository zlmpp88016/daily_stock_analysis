# Claude Code 技能汇总

> 自动生成于 2026-03-15
> 总计：36 个技能

---

## 📋 目录

- [工作流技能 (Workflow)](#工作流技能-workflow) - 7 个
- [团队协作技能 (Team)](#团队协作技能-team) - 19 个
- [独立技能 (Standalone)](#独立技能-standalone) - 3 个
- [审查技能 (Review)](#审查技能-review) - 2 个
- [工具类技能 (Utility)](#工具类技能-utility) - 3 个
- [元技能 (Meta)](#元技能-meta) - 2 个

---

## 工作流技能 (Workflow)

### 1. workflow-lite-plan
**轻量级规划工作流**

快速任务规划与执行流水线，适合简单明确的开发任务。

**流程：** 探索 → 规划 → 确认 → 执行

**触发词：** `lite-plan`, `快速任务`, `简单规划`

**适用场景：**
- 添加简单功能
- 修复明确的 bug
- 快速原型开发

---

### 2. workflow-plan
**正式规划工作流**

完整的 4 阶段规划流程，包含会话管理、上下文分析、约定检查、计划生成和验证。

**流程：** 会话 → 上下文 → 约定 → 生成 → 验证

**触发词：** `workflow-plan`, `正式规划`, `详细计划`

**适用场景：**
- 复杂功能开发
- 需要详细设计的任务
- 多模块协作

---

### 3. workflow-execute
**执行工作流**

基于规划文档执行开发任务，支持会话发现、任务处理和自动提交。

**流程：** 会话发现 → 任务处理 → 提交

**触发词：** `workflow-execute`, `执行计划`, `开始开发`

**适用场景：**
- 执行已规划的任务
- 批量任务处理
- 自动化开发流程

---

### 4. workflow-tdd-plan
**TDD 工作流**

测试驱动开发完整流程，包含 6 阶段 TDD 规划和 Red-Green-Refactor 任务链生成。

**流程：** TDD 规划 → 任务链生成 → 合规验证

**触发词：** `tdd-plan`, `测试驱动`, `TDD 开发`

**适用场景：**
- 测试优先开发
- 高质量代码要求
- 重构现有代码

---

### 5. workflow-test-fix
**测试修复工作流**

结合测试生成和迭代测试修复的完整流水线，支持自适应策略和 CLI 回退。

**流程：** 会话 → 上下文 → 分析 → 生成 → 循环修复

**触发词：** `test-fix`, `测试修复`, `修复失败测试`

**适用场景：**
- 修复失败的测试
- 提高测试覆盖率
- 测试驱动的 bug 修复

---

### 6. workflow-multi-cli-plan
**多 CLI 协作规划**

使用 ACE 上下文收集和多个 CLI 工具进行协作式规划。

**流程：** ACE 上下文 → CLI 讨论 → 规划 → 执行

**触发词：** `multi-cli`, `多 CLI 协作`, `协作规划`

**适用场景：**
- 需要多角度分析的任务
- 复杂架构设计
- 跨模块重构

---

### 7. workflow-skill-designer
**工作流技能设计器**

元技能，用于设计新的工作流技能，创建协调器和阶段式加载结构。

**流程：** 需求分析 → 结构设计 → 生成 SKILL.md

**触发词：** `design workflow skill`, `创建工作流技能`

**适用场景：**
- 创建新的工作流模式
- 定制化开发流程
- 扩展 CCW 能力

---

## 团队协作技能 (Team)

### 8. team-planex
**规划执行团队**

规划 + 执行的 wave pipeline，适合清晰的 issue 或 roadmap 驱动开发。

**架构：** planner + executor

**触发词：** `team-planex`, `规划执行`, `波次开发`

**适用场景：**
- Roadmap 驱动开发
- 批量 issue 处理
- 分阶段交付

---

### 9. team-lifecycle-v4
**完整生命周期团队 v4**

优化版完整生命周期，使用 team-worker agent 架构和 role-specs。

**架构：** Coordinator + team-worker agents

**触发词：** `team-lifecycle-v4`, `完整生命周期`

**适用场景：**
- 从需求到部署的完整流程
- 规范化开发流程
- 大型功能开发

---

### 10. team-coordinate
**通用团队协调**

动态生成角色规范的通用团队协调器。

**架构：** 运行时动态生成 role-specs

**触发词：** `team-coordinate`, `团队协调`, `动态团队`

**适用场景：**
- 灵活的团队组织
- 临时性协作任务
- 自定义角色分工

---

### 11. team-brainstorm
**团队头脑风暴**

多角度分析和创意生成的团队协作。

**架构：** team-worker agents with role directories

**触发词：** `team-brainstorm`, `团队头脑风暴`, `多角度分析`

**适用场景：**
- 架构设计讨论
- 技术方案选型
- 创新功能探索

---

### 12. team-frontend
**前端开发团队**

专注于前端开发的团队技能。

**架构：** Frontend specialists

**触发词：** `team-frontend`, `前端团队`, `前端开发`

**适用场景：**
- React/Vue 组件开发
- UI 实现
- 前端架构设计

---

### 13. team-frontend-debug
**前端调试团队**

使用 Chrome DevTools MCP 进行前端调试，支持功能列表测试和 bug 报告调试。

**架构：** Dual-mode debugging

**触发词：** `team-frontend-debug`, `前端调试`

**适用场景：**
- 浏览器端 bug 调试
- 性能问题分析
- UI 交互问题排查

---

### 14. team-issue
**Issue 解决团队**

专注于 issue 解决的流水线团队。

**架构：** Issue resolution pipeline

**触发词：** `team-issue`, `issue 团队`, `问题解决`

**适用场景：**
- Bug 修复
- Issue 批量处理
- 问题跟踪和解决

---

### 15. team-iterdev
**迭代开发团队**

支持迭代式开发的团队协作。

**架构：** Iterative development

**触发词：** `team-iterdev`, `迭代开发`, `敏捷开发`

**适用场景：**
- 敏捷开发流程
- 快速迭代
- 持续改进

---

### 16. team-perf-opt
**性能优化团队**

专注于性能优化的团队协作，Coordinator 编排流水线，Workers 执行优化任务。

**架构：** Coordinator + workers

**触发词：** `team-perf-opt`, `性能优化`, `性能团队`

**适用场景：**
- 应用性能优化
- 代码性能分析
- 资源使用优化

---

### 17. team-review
**代码审查团队**

代码扫描和漏洞审查团队。

**架构：** Scanning + vulnerability review

**触发词：** `team-review`, `代码审查团队`, `安全审查`

**适用场景：**
- 代码质量审查
- 安全漏洞扫描
- 合规性检查

---

### 18. team-roadmap-dev
**Roadmap 驱动开发团队**

从需求到实现的 roadmap 驱动开发。

**架构：** Requirement → implementation

**触发词：** `team-roadmap-dev`, `roadmap 开发`, `路线图开发`

**适用场景：**
- 产品路线图实现
- 长期规划执行
- 分阶段交付

---

### 19. team-tech-debt
**技术债务清理团队**

识别和修复技术债务的团队协作。

**架构：** Debt identification + cleanup

**触发词：** `team-tech-debt`, `技术债务`, `代码清理`

**适用场景：**
- 代码重构
- 技术债务偿还
- 代码质量提升

---

### 20. team-testing
**测试团队**

通过 Generator-Critic 循环实现渐进式测试覆盖。

**架构：** Test planning + execution

**触发词：** `team-testing`, `测试团队`, `测试覆盖`

**适用场景：**
- 测试用例生成
- 测试覆盖率提升
- 质量保证

---

### 21. team-quality-assurance
**质量保证团队**

完整的闭环 QA，结合 issue 发现和软件测试。

**架构：** Issue discovery + testing

**触发词：** `team-quality-assurance`, `QA 团队`, `质量保证`

**适用场景：**
- 全面质量检查
- 发布前验证
- 持续质量监控

---

### 22. team-uidesign
**UI 设计团队**

UI 设计流程：研究 → 设计令牌 → 审计 → 实现。

**架构：** Design system + prototyping

**触发词：** `team-uidesign`, `UI 设计团队`, `界面设计`

**适用场景：**
- UI/UX 设计
- 设计系统构建
- 原型开发

---

### 23. team-ux-improve
**UX 改进团队**

系统性发现和修复 UI/UX 交互问题，包括无响应按钮、交互延迟等。

**架构：** UX analysis + improvement

**触发词：** `team-ux-improve`, `UX 改进`, `用户体验优化`

**适用场景：**
- 用户体验优化
- 交互问题修复
- 可用性提升

---

### 24. team-ultra-analyze
**深度协作分析团队**

深度协作分析，所有角色通过 SKILL.md 路由。

**架构：** Coordinator-only (monitor.md)

**触发词：** `team-ultra-analyze`, `深度分析`, `协作分析`

**适用场景：**
- 复杂问题分析
- 多维度评估
- 深度技术调研

---

### 25. team-executor
**轻量执行团队**

恢复现有 team-coordinate 会话进行纯执行。

**架构：** Session resumption

**触发词：** `team-executor`, `轻量执行`, `恢复会话`

**适用场景：**
- 恢复中断的任务
- 继续执行计划
- 会话管理

---

### 26. team-arch-opt
**架构优化团队**

使用 team-worker agent 架构进行架构优化，Coordinator 编排，Workers 执行优化。

**架构：** Coordinator + workers with role directories

**触发词：** `team-arch-opt`, `架构优化`, `架构团队`

**适用场景：**
- 系统架构优化
- 架构重构
- 技术选型

---

## 独立技能 (Standalone)

### 27. brainstorm
**头脑风暴**

双模式头脑风暴：自动流水线或单角色分析。

**模式：** auto pipeline / single role

**触发词：** `brainstorm`, `头脑风暴`, `创意生成`

**适用场景：**
- 创意生成
- 方案探索
- 问题分析

---

### 28. spec-generator
**规格文档生成器**

6 阶段规格文档链：产品简介 → PRD → 架构 → Epic。

**流程：** product-brief → PRD → architecture → epics

**触发词：** `spec-generator`, `规格生成`, `文档生成`

**适用场景：**
- 产品文档编写
- 需求规格说明
- 架构文档生成

---

### 29. simplify
**代码简化**

审查修改后的代码，检查复用性、质量和效率，然后修复发现的问题。

**触发词：** `simplify`, `代码简化`, `优化代码`

**适用场景：**
- 代码重构
- 提高代码质量
- 消除冗余

---

## 审查技能 (Review)

### 30. review-code
**代码审查**

多维度代码审查，分析正确性、可读性、性能、安全性、测试和架构。

**维度：** 正确性、可读性、性能、安全、测试、架构

**触发词：** `review code`, `code review`, `审查代码`, `代码审查`

**适用场景：**
- Pull Request 审查
- 代码质量检查
- 安全审计

---

### 31. review-cycle
**审查循环**

多维度代码审查 + 自动修复编排，支持会话模式、模块模式和修复模式。

**模式：** session-based / module-based / fix mode

**触发词：** `workflow:review-cycle`, `审查循环`, `自动修复`

**适用场景：**
- 持续代码审查
- 自动化修复
- 质量改进循环

---

## 工具类技能 (Utility)

### 32. ccw-help
**CCW 帮助系统**

命令搜索、浏览、推荐，Skill/Team 目录查看。

**功能：** 搜索、浏览、推荐

**触发词：** `ccw-help`, `ccw-issue`, `帮助`, `命令`

**适用场景：**
- 查找命令
- 学习工作流
- 获取帮助

---

### 33. issue-manage
**Issue 管理**

交互式 issue 管理，支持菜单驱动的 CRUD 操作。

**功能：** 创建、查看、编辑、删除、批量操作

**触发词：** `manage issue`, `list issues`, `issue 管理`

**适用场景：**
- Issue 跟踪
- 任务管理
- 批量操作

---

### 34. memory-capture
**记忆捕获**

统一记忆捕获，支持会话压缩和快速提示。

**模式：** session compact / quick tips

**触发词：** `memory capture`, `compact session`, `记录`, `压缩会话`

**适用场景：**
- 保存会话要点
- 记录经验教训
- 知识积累

---

### 35. memory-manage
**记忆管理**

统一记忆管理，CLAUDE.md 更新和文档生成。

**功能：** CLAUDE.md 更新、文档生成

**触发词：** `memory manage`, `update claude`, `更新记忆`, `生成文档`

**适用场景：**
- 更新项目配置
- 生成文档
- 知识管理

---

## 元技能 (Meta)

### 36. command-generator
**命令生成器**

5 阶段工作流，创建带 YAML frontmatter 的 Claude Code 命令文件。

**流程：** 5 phase workflow

**触发词：** `create command`, `new command`, `命令生成器`

**适用场景：**
- 创建新命令
- 扩展 CCW 功能
- 自定义工作流

---

## 📊 统计信息

| 类别 | 数量 | 占比 |
|------|------|------|
| 团队协作 (Team) | 19 | 52.8% |
| 工作流 (Workflow) | 7 | 19.4% |
| 独立技能 (Standalone) | 3 | 8.3% |
| 审查 (Review) | 2 | 5.6% |
| 工具类 (Utility) | 3 | 8.3% |
| 元技能 (Meta) | 2 | 5.6% |
| **总计** | **36** | **100%** |

---

## 🚀 快速开始

### 常用工作流推荐

**简单任务：**
```bash
/workflow-lite-plan "添加用户登录功能"
```

**复杂任务：**
```bash
/workflow-plan "重构认证模块"
/workflow-execute
```

**测试驱动：**
```bash
/workflow-tdd-plan "实现支付接口"
```

**团队协作：**
```bash
/team-planex "用户系统 roadmap"
```

**代码审查：**
```bash
/review-cycle
```

---

## 📖 相关文档

- [CCW 命令系统](../commands/ccw.md)
- [工作流指南](../workflows/)
- [团队技能架构](../skills/team-*/SKILL.md)

---

*本文档由 ccw-help 技能自动生成*
