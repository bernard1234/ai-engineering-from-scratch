# LLM 的 FinOps —— Unit Economics 与多租户归因

> 传统 FinOps 在 LLM 支出上会失效。成本是 token 交易，而非资源在线时长。标签映射不上 —— 一次 API 调用是一笔交易，不是一个资产。工程决策（prompt 设计、context window、输出长度）就是财务决策。2026 年的打法有第一天就要埋好的三个归因维度：按用户（`user_id`）用于席位定价与扩容，按任务（`task_id` + `route`）用于产品面成本与优先级，按租户（`tenant_id`）用于 unit economics 与续约。四个 token 层 —— prompt、tool、memory、response —— 混在一个桶里就藏住了支出。多租户产品的执行阶梯：按租户限流（期望峰值的 2-3 倍，清晰的 429 + retry-after）；日消费上限（合同上限的 1.5-3 倍；触发收紧限流 + 告警）；消费 z-score > 4 时触发 kill switch（自动暂停 + 呼叫 on-call）。归因模式：tag-and-aggregate、telemetry-joiner（trace-ID → 账单；准确率最高）、采样与外推、基于模型的分配、事件溯源、实时流式。单位指标：每个已解决查询的成本、每个生成产物的成本 —— 而不是 $/M token。事后补标签总会漏；在请求创建时就埋点。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级带 kill switch 的成本归因模拟器)
**Prerequisites:** 第 17 阶段，第 13 课（Observability），第 14 课（Caching）
**Time:** ~60 分钟

## Learning Objectives

- 解释为什么传统 FinOps（标签 + 分层）在 LLM 支出上失效，并说出三个新的归因维度。
- 列举四个 token 层（prompt、tool、memory、response），以及为什么单桶计费会藏住成本。
- 为一个多租户产品设计执行阶梯（限流 → 消费上限 → kill switch）。
- 选择单位指标（每个已解决查询 / 产物的成本），而不是 $/M token。

## 问题场景

你的账单写着 $40,000。你不知道：
- 哪个租户花的。
- 哪个产品功能驱动的。
- 是否有某个用户滥用。
- 罪魁祸首是 prompt 膨胀、tool call，还是 memory 放大。

供应商侧的 tag-and-aggregate 适用于云资源（EC2、S3），那里的标签会传播到账单行。LLM API 调用不会自动打标 —— 你得在调用点打上 user/task/tenant 并一路携带。事后归因总会漏掉边角情况。

## 核心概念

### 三个归因维度

**按用户（Per-user）**（`user_id`）：谁在花多少钱。驱动席位定价、扩容对话，识别重度用户。

**按任务（Per-task）**（`task_id` + `route`）：哪个产品面花多少钱。驱动功能优先级、砍掉昂贵功能的决策。

**按租户（Per-tenant）**（`tenant_id`）：哪个客户在盈利。驱动 unit economics、续约定价、分层阈值。

第一天就在调用点埋好这三者。事后补做总是更差。

### 四个 token 层

| 层 | 示例 | 占总量的典型百分比 |
|-------|---------|---------------------|
| Prompt | system + 用户输入 | 40-60% |
| Tool | 回喂的 tool-call 结果 | 20-40%（agent 工作负载） |
| Memory | 历史对话 / 检索到的文档 | 10-30% |
| Response | 模型输出 | 10-30% |

把四者混在一个桶里会让优化变盲。在你的归因 schema 里把它们拆开。

### 执行阶梯

1. **限流（Rate limit）** 按租户。期望峰值的 2-3 倍。返回 429 并带 `Retry-After`。租户感受到摩擦；不会收到意外账单。

2. **日消费上限** 按租户。合同上限的 1.5-3 倍。触发动作：收紧限流 + 通知客户成功团队。

3. **Kill switch** 在消费 z-score 相对租户基线 > 4 时触发。自动暂停租户；呼叫 on-call；升级到运维 + CS。

### 归因模式

- **Tag-and-aggregate**：打上元数据头；之后再聚合。简单；粗糙。
- **Telemetry joiner**：通过 trace ID 把 traces 关联到账单。准确率最高。成熟团队的做法。
- **采样 + 外推**：采样 5-10%，再放大。对粗略消费估算性价比高；会漏掉长尾。
- **基于模型的分配**：用回归推断成本驱动项。适用于没有标签的遗留数据。
- **事件溯源**：把成本作为流中的事件（Kafka / Kinesis）。实时。
- **实时流式**：看板亚秒级更新。

### 每 X 成本才是单位指标

$/M token 是厂商话术。产品指标是：

- 每个已解决支持工单的成本。
- 每篇生成文章的成本。
- 每个成功 agent 任务的成本。
- 每用户会话分钟的成本。

把成本绑到一个产品结果上。否则优化就没有锚点。

### 成本归因 trace 结构

```
trace_id: abc123
  user_id: u_42
  tenant_id: t_7
  task_id: task_classify_doc
  route: model_haiku
  layers:
    prompt_tokens: 1800
    tool_tokens: 600
    memory_tokens: 400
    response_tokens: 150
  cost_usd: 0.0135
  cached_input: true
  batch: false
```

每次调用都发出。存进数据湖。按维度聚合。Phase 17 · 13 的可观测性栈就是它所在之处。

### 叠加节省栈

叠起来：cache + batch + route + gateway。四者齐备时：
- Cache L2（Phase 17 · 14）：输入便宜约 10 倍。
- Batch（Phase 17 · 15）：打 5 折。
- 路由到便宜模型（Phase 17 · 16）：成本降低 60%。
- Gateway 效率（Phase 17 · 19）：冗余 + 重试。

最佳情况下叠加：约为朴素基线的 5-10%。大多数团队只启用 2-3 个杠杆；很少四个全叠。

### 需要记住的数字

- 归因维度：按用户、按任务、按租户。
- 四个 token 层：prompt、tool、memory、response。
- Kill switch：消费 z-score > 4。
- 单位指标：每个已解决查询的成本，而非 $/M token。
- 叠加优化：可能降到基线的约 5-10%。

```figure
i4-spend-ladder
```

## Use It

`code/main.py` 模拟一个带三层执行阶梯的多租户 LLM 服务。注入一个滥用租户，演示 kill switch 触发。

## Ship It

本课产出 `outputs/skill-finops-plan.md`。给定产品与规模，设计归因 schema 与执行阶梯。

## Exercises

1. 运行 `code/main.py`。kill switch 在多少 z-score 时触发？你如何选阈值？
2. 设计一个按租户、按任务的成本看板。你先构建的 5 个视图是什么？
3. 你最大的租户 unit economics 为负。按客户影响排序提出三种干预措施。
4. 为一个支持类产品计算每个已解决工单的成本：每工单 3M token、每天约 800 个工单、GPT-5 cached 费率。
5. 论证事后打标签是否可能奏效。什么时候可以接受？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Per-user attribution | “用户级成本” | 每次调用都打上 `user_id` |
| Per-task attribution | “功能成本” | `task_id` + `route` 标识产品面 |
| Per-tenant attribution | “客户成本” | `tenant_id`；驱动 unit economics |
| Four token layers | “成本层” | prompt + tool + memory + response |
| Rate limit | “429 守卫” | 在 gateway 强制执行的按租户上限 |
| Daily spend cap | “日上限” | 带告警的租户级预算 |
| Kill switch | “自动暂停” | 消费 z-score > 4 触发自动挂起 |
| Cost per resolved | “产品单位指标” | 与产品结果挂钩的成本，而非 token |
| Telemetry joiner | “trace 到账单” | 准确率最高的归因模式 |
| Stacked optimization | “cache+batch+route+gateway” | 复利式节省，降到约基线的 5-10% |

## Further Reading

- [FinOps Foundation —— FinOps for AI 概览](https://www.finops.org/wg/finops-for-ai-overview/)
- [FinOps School —— 单位成本 2026 指南](https://finopsschool.com/blog/cost-per-unit/)
- [Digital Applied —— LLM Agent 成本归因 2026](https://www.digitalapplied.com/blog/llm-agent-cost-attribution-guide-production-2026)
- [PointFive —— Azure OpenAI 中的托管 LLM](https://www.pointfive.co/blog/finops-for-ai-economics-of-managed-llms-in-azure-open-ai)
