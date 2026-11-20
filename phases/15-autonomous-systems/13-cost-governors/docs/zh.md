# 动作预算、迭代上限与成本治理器

> 一个中型电商 agent 在其团队启用“订单追踪”技能后，月度 LLM 成本从 $1,200 跳到 $4,800。这不是定价 bug。这是一个 agent 找到了一个新的循环，并在其中持续花钱。Microsoft 的 Agent Governance Toolkit（2026 年 4 月 2 日）把针对这一类问题的防御整理成规范：按请求的 `max_tokens`、按任务的 token 与美元预算、按天/月的上限、迭代上限、分层模型路由、prompt caching、context windowing、昂贵动作上的 HITL checkpoint、预算超限时的 kill switch。Anthropic 的 Claude Code Agent SDK 以不同的名称提供了同样的原语。资金速率限制——例如 10 分钟内消费超过 $50 就切断访问——比月度上限更快地捕获循环。

**Type:** Learn
**Languages:** Python（stdlib，分层成本治理器模拟器）
**Prerequisites:** 第 15 阶段，第 10 课（Permission modes）、第 15 阶段，第 12 课（Durable execution）
**Time:** ~60 分钟

## 问题场景

自主 agent 每一轮都在花真金白银。聊天机器人输出糟糕，只是一个糟糕的回复；agent 的糟糕循环，则是一张账单。业界对这种失败模式有记录的术语叫“Denial of Wallet”——agent 持续推理、持续调用工具、持续计费，没有任何东西能阻止它，因为没有任何东西被设计来阻止它。

解决办法不是一个数字。而是一个由不同时间尺度和粒度的限制组成的栈：按请求、按任务、按小时、按天、按月。设计良好的栈能在几分钟内捕获失控循环、在几小时内捕获缓慢泄漏、在一天内捕获糟糕的发布。当 agent 是长程且自主的时候，也是同一个栈让预算得以维持。

这是一节工程课：数学很简单，团队失败的地方在于纪律。下面列出的限制清单，全部都在 Microsoft Agent Governance Toolkit 或 Anthropic Claude Code Agent SDK 文档中被点名过。

## 核心概念

### 成本治理器栈

1. **按请求的 `max_tokens`。** 简单。防止任何一次调用输出无界的补全。
2. **按任务的 token 预算。** 整个运行期间，不超过 N 个 token。到达上限即硬停。
3. **按任务的美元预算。** 与 token 相同，但以货币计。Claude Code 中为 `max_budget_usd`。
4. **按工具的调用上限。** `WebFetch` 调用不超过 N 次、`shell_exec` 调用不超过 N 次，依此类推。
5. **迭代上限（`max_turns`）。** agent 循环的总迭代次数；防止无限推理循环。
6. **按分钟 / 按小时 / 按天 / 按月上限。** 滚动窗口。在不同时间尺度上捕获泄漏。
7. **资金速率限制。** 例如“若 10 分钟内消费超过 $50，就切断访问”。在月度上限触发之前，捕获基于循环的烧钱。
8. **分层模型路由。** 默认使用较小的模型；只有当分类器判断任务需要时才升级到较大的模型。
9. **Prompt caching。** 系统 prompt 与稳定 context 存入 provider 缓存；重新发送的 token 成本接近零。
10. **Context windowing。** 通过压缩 / 摘要让活跃 context 低于阈值；直接降低 token 成本。
11. **昂贵动作上的 HITL checkpoint。** 在已知昂贵的动作（长工具调用、大下载、昂贵的模型升级）之前，要求人工点一下确认。
12. **预算超限时的 kill switch。** 任一项上限触发时会话中止。上限被记录；需要走单独的重新启用路径。

### 为什么是栈，而不是单个上限

单个月度上限只有在钱包空了之后才捕获失控 agent。单个按请求上限在会话层面什么都捕获不到。不同的失败模式需要不同的时间尺度：

- **失控循环**（agent 陷入 5 秒重试）：由速率限制捕获。
- **缓慢泄漏**（agent 每个任务做了约 2 倍于预期的工作）：由按天上限捕获。
- **糟糕发布**（新版本使用 5 倍 token）：由按周 / 按月上限捕获。
- **合法激增**（真实需求，而非 bug）：由按小时 / 按天上限捕获，并留下清晰的日志。

### 一个 harness 的预算表面

Claude Code Agent SDK 暴露（公开文档）：

- `max_turns` —— 迭代上限。
- `max_budget_usd` —— 美元上限；超限时会话中止。
- `allowed_tools` / `disallowed_tools` —— 工具白名单与黑名单。
- 工具使用之前的 hook 点，用于自定义成本核算。

与权限模式阶梯（第 10 课）结合。一个没有 `max_budget_usd` 的 `autoMode` 会话就是无治理的自主性。Anthropic 明确指出 Auto Mode 需要预算控制；分类器与成本是正交的。

### EU AI Act、OWASP Agentic Top 10

Microsoft 的 Agent Governance Toolkit 覆盖 OWASP Agentic Top 10 以及 EU AI Act 第 14 条（人类监督）的要求。在欧盟用于生产时，日志记录与上限执行不是可选项。

### 观察到的 $1,200 → $4,800 案例

Microsoft 文档中的真实案例：一个电商 agent 在新增一个工具后月度成本涨到三倍。该工具允许 agent 在每个会话中轮询订单状态。没有循环检测。没有按工具上限。没有对周环比增长的告警。修复方案是按工具上限加上每日增长告警。这是一个模板：每个新的工具面都是一个新的潜在循环；每个新工具都需要自己的上限和自己的告警。

```figure
cost-governor-stack
```

## Use It

`code/main.py` 模拟一次带与不带分层成本治理器栈的 agent 运行。被模拟的 agent 在若干轮之后漂移进一个轮询循环；分层栈在速率窗口内就捕获了它，而单个月度上限要到数天之后才会触发。

## Ship It

`outputs/skill-agent-budget-audit.md` 审计一次拟议 agent 部署的成本治理器栈，并标出缺失的层。

## Exercises

1. 运行 `code/main.py`。确认在轮询循环轨迹上，速率限制先于迭代上限触发。然后禁用速率限制，测量在迭代上限捕获它之前 agent“花掉”了多少。

2. 为浏览器 agent（第 11 课）设计一套按工具的上限。哪个工具需要最紧的上限？哪个工具可以无风险地无界运行？

3. 阅读 Microsoft Agent Governance Toolkit 文档。列出该 toolkit 点名的每一种上限类型。把每一种映射到某一种失败模式（失控循环、缓慢泄漏、糟糕发布、激增）。

4. 为一个真实任务（例如“在某个 repo 中分诊 50 个 issue”）给一次夜间无人值守运行的定价。把 `max_budget_usd` 设为你的点估计的 2 倍。说明为什么是 2 倍。

5. Claude Code 的 `max_budget_usd` 在会话总成本上触发。设计一个你会从外部强制执行的补充性速率限制。什么触发切断，重新启用又是什么样子？

## Key Terms

| 术语 | 人们的说法 | 实际含义 |
|---|---|---|
| Denial of Wallet | “失控账单” | agent 循环产生消费，且没有上限能阻止它 |
| max_tokens | “按请求上限” | 单次补全大小的上限 |
| max_turns | “迭代上限” | 会话中 agent 循环迭代次数的上限 |
| max_budget_usd | “美元 kill switch” | 会话成本上限；超限即中止 |
| Velocity limit | “速率上限” | 每个短窗口内的消费限制（例如 $50 / 10 分钟） |
| Tiered routing | “小模型优先” | 默认用便宜模型；仅在分类器判断需要时升级 |
| Prompt caching | “缓存的系统 prompt” | provider 侧缓存把重发 token 成本降到接近零 |
| HITL checkpoint | “人工批准闸门” | 昂贵动作之前要求人工点确认 |

## Further Reading

- [Anthropic Claude Code Agent SDK — agent loop and budgets](https://code.claude.com/docs/en/agent-sdk/agent-loop) — `max_turns`、`max_budget_usd`、工具白名单。
- [Microsoft Agent Framework — human-in-the-loop and governance](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — 成本治理器 checkpoint。
- [Anthropic — Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) — provider 侧成本控制。
- [Anthropic — Prompt caching (Claude API docs)](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — 缓存机制。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 长程 agent 的成本画像。
