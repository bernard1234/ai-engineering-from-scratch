# Human-in-the-Loop：propose-then-commit

> 2026 年关于 HITL 的共识是具体的。它不是“agent 提问、用户点 Approve”。它是 propose-then-commit：拟议动作以带 idempotency key 的形式持久化到一个持久存储中；连同意图、数据血统、所触及的权限、影响范围和 rollback 计划一起呈现给审查者；只有在获得肯定确认后才 commit；执行后加以验证，确认副作用确实发生了。LangGraph 的 `interrupt()` 加 PostgreSQL checkpoint、Microsoft Agent Framework 的 `RequestInfoEvent`、以及 Cloudflare 的 `waitForApproval()` 都实现了相同的形状。典型的失败模式是橡皮图章式批准：“Approve？”未经审查就被点击。有记录的缓解手段是带明确清单的 challenge-and-response。

**Type:** Learn
**Languages:** Python（stdlib，带 idempotency 的 propose-then-commit 状态机）
**Prerequisites:** 第 15 阶段，第 12 课（Durable execution）、第 15 阶段，第 14 课（Tripwires）
**Time:** ~60 分钟

## 问题场景

agent 要采取一个动作。用户必须决定：批准还是不批准。如果决策是瞬时的，那很可能不是一次审查。如果决策是结构化的，它慢但可信。工程问题是：如何让结构化的审查成为阻力最小的路径。

2023 年时代的 HITL 模式是同步提示：“Agent 想给 X 发一封正文为 Y 的邮件——批准？”用户点 Approve。大家都觉得系统是安全的。实际上这个表面被大量地橡皮图章式处理：用户批准得很快，批准几乎不预测任何东西，而当 agent 出错时，审计轨迹显示出一长串用户记不起来的批准。

2026 年的模式——propose-then-commit——把 HITL 移到持久的基底上，附带结构化的元数据，并要求肯定式 commit。每个托管 agent SDK 都提供了一种版本：LangGraph `interrupt()`、Microsoft Agent Framework `RequestInfoEvent`、Cloudflare `waitForApproval()`。API 名称不同；形状相同。

## 核心概念

### Propose-then-commit 状态机

1. **Propose。** agent 产出一个拟议动作。持久化到一个持久存储（PostgreSQL、Redis、Durable Object）。包含：
   - 意图（agent 为什么这么做）
   - 数据血统（哪个来源导致了这个提议）
   - 所触及的权限（哪些 scope / 文件 / 端点）
   - 影响范围（最坏情况是什么）
   - rollback 计划（如果 commit 了，我们如何撤销它）
   - idempotency key（每个提议唯一；重新提交返回同一条记录）
2. **Surface。** 审查者看到带全部元数据的提议。审查者是一个人（不是 agent 审查自己）。
3. **Commit。** 肯定式确认。动作执行。
4. **Verify。** 执行后，副作用被读回并加以确认。如果 verify 步骤失败，系统处于已知的坏状态，告警启动。

### Idempotency key

没有 idempotency key，一次瞬时失败之后的重试可能双重执行一个已批准的动作。具体例子：用户批准“从 A 向 B 转账 $100”。网络抖动。workflow 重试。用户只批准了一次，但转账执行了两次。idempotency key 把批准绑定到单个唯一的副作用上；第二次执行变成 no-op。

这与 Stripe 和 AWS API 使用的是同一个 idempotency 模式。把它复用于 agent 批准这一点，Microsoft Agent Framework 文档有明确说明。

### 持久化：为什么批准能比进程活得更久

批准等待室是一块 agent 并不拥有的状态。workflow 被暂停（第 12 课）。当批准到达时，workflow 正好从那个点恢复。这就是为什么 LangGraph 把 `interrupt()` 与 PostgreSQL checkpoint 配对，而不只是内存中的状态——两天后到达的批准仍然能找到完好无损的 workflow。

### 橡皮图章式批准与 challenge-and-response 缓解

HITL 的默认 UI（“Approve” / “Reject” 按钮）会产生没有真正审查的快速批准。有记录的缓解：一份 challenge-and-response 清单，要求在 Approve 按钮启用之前对特定问题给出肯定回答。具体形状：

- “你了解这次操作触及什么资源吗？[ ]”
- “你核实过影响范围可以接受吗？[ ]”
- “如果失败，你有 rollback 计划吗？[ ]”

这不是为了官僚而官僚——这是一个强制函数。无法勾选的审查者要么要求澄清（升级），要么拒绝（安全默认）。Anthropic 的 agent 安全研究明确把清单驱动的 HITL 列为对橡皮图章式批准模式的缓解。

### 什么算有后果

并非每个动作都需要 propose-then-commit。2026 年的指引：

- **有后果的动作**（总是 HITL）：不可逆写入、金融交易、对外通信、生产数据库变更、破坏性的文件系统操作。
- **可逆的动作**（有时 HITL）：对本地文件的编辑、预发环境变更、有清晰 rollback 的可逆写入。
- **读取与检查**（从不 HITL）：读取文件、罗列资源、调用只读 API。

### 动作后验证

“commit 跑过了”与“副作用发生了”并不相同。网络分区和竞态条件可能产生一个自认为成功、而后端并未持久化的 workflow。verify 步骤在 commit 之后重新读取目标资源以确认。这与带 `RETURNING` 子句的数据库事务、或 `PutObject` 之后的 AWS `GetObject` 是同一个模式。

### EU AI Act 第 14 条

第 14 条要求在欧盟的高风险 AI 系统具备有效的人类监督。“有效”并非装饰。监管语言明确排除橡皮图章模式。在 Microsoft Agent Governance Toolkit 的合规文档中，带 challenge-and-response 的 propose-then-commit 是能通过第 14 条审查的形状。

```figure
mx-propose-then-commit
```

## Use It

`code/main.py` 用 stdlib Python 实现了一个 propose-then-commit 状态机。持久存储是一个 JSON 文件。idempotency key 是 (thread_id, action_signature) 的哈希。驱动程序模拟三种情况：一个干净的批准流程、一次瞬时失败后的重试（必须不双重执行），以及橡皮图章默认方式与 challenge-and-response 流程的对比。

## Ship It

`outputs/skill-hitl-design.md` 审查一次拟议的 HITL 工作流是否符合 propose-then-commit 形状，并标出缺失的元数据、idempotency、验证或 challenge-and-response 层。

## Exercises

1. 运行 `code/main.py`。确认对一个已批准提议的重试使用持久记录，不重新执行。然后把时间戳加入 idempotency key，展示重试会双重执行。

2. 用 `rollback` 字段扩展提议记录。模拟一次 verify 步骤失败的执行。展示 rollback 自动触发。

3. 阅读 Microsoft Agent Framework 的 `RequestInfoEvent` 文档。找出 API 包含、而玩具引擎缺失的一个元数据字段。加上它，并解释它能防范什么。

4. 为某个具体动作（例如“发布到公开的 Twitter 账号”）设计一份 challenge-and-response 清单。审查者必须回答哪三个问题？为什么是这三个？

5. 挑选一个同步“Approve？”提示已足够（不需要持久存储）的情况。解释原因，并说出你所接受的风险类别。

## Key Terms

| 术语 | 人们的说法 | 实际含义 |
|---|---|---|
| Propose-then-commit | “两阶段批准” | 持久化的提议 + 肯定式 commit + verify |
| Idempotency key | “可安全重试的 token” | 每个提议唯一；第二次执行变成 no-op |
| Data lineage | “它从哪里来” | 导致该提议的具体来源内容 |
| Blast radius | “最坏情况” | 动作出错时的影响范围 |
| Rubber-stamp | “快速批准” | 未经真正审查就点击“Approve” |
| Challenge-and-response | “强制清单” | 审查者必须对特定问题作出肯定确认 |
| RequestInfoEvent | “MS Agent Framework 原语” | 带结构化元数据的持久 HITL 请求 |
| `interrupt()` / `waitForApproval()` | “框架原语” | 相同形状的 LangGraph / Cloudflare 对应物 |

## Further Reading

- [Microsoft Agent Framework — Human in the loop](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — `RequestInfoEvent`、持久批准。
- [Cloudflare Agents — Human in the loop](https://developers.cloudflare.com/agents/concepts/human-in-the-loop/) — `waitForApproval()` 与 Durable Objects。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 作为长程风险缓解的 HITL。
- [EU AI Act — Article 14: Human oversight](https://artificialintelligenceact.eu/article/14/) — 高风险系统的监管基线。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 围绕监督的宪法框架。
