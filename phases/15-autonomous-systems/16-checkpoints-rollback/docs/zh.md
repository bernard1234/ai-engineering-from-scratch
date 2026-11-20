# Checkpoint 与回滚

> 每一次图状态转换都会持久化。当某个 worker 崩溃时，它的租约过期，另一个 worker 从最新的 checkpoint 继续。Cloudflare Durable Objects 可以在数小时乃至数周内持有状态。Propose-then-commit（第 15 课）为每个动作定义了回滚方案。动作后校验闭合了整个回路。EU AI Act Article 14 要求高风险系统具备有效的人类监督——落到实处，这意味着 checkpoint 必须可查询、rollback 必须经过演练、审计轨迹必须能在一次部署后存活。最尖锐的失效模式是：没有 idempotency key 和 precondition check 时，一次瞬时失败后的重试可能把一个已经获批的动作执行两次。动作后校验正是用来抓住它的。

**Type:** Learn
**Languages:** Python (stdlib, checkpoint and rollback state machine)
**Prerequisites:** 第 15 阶段，第 12 课（Durable execution）、第 15 阶段，第 15 课（Propose-then-commit）
**Time:** ~60 分钟

## 问题场景

Durable execution（第 12 课）让崩溃的 agent 可以恢复。Propose-then-commit（第 15 课）让获批的动作可审计。本课把二者接起来：当一个获批动作执行到一半、崩溃、然后恢复时会发生什么？rollback 在什么时候运行，针对哪一份状态运行？

真实系统对此的接线方式各不相同：

- **LangGraph** 把每一次图状态转换 checkpoint 到 PostgreSQL。worker 崩溃时租约释放，另一个 worker 从最新的 checkpoint 恢复。工作流在 `interrupt()` 处暂停，而 `interrupt()` 本身也会持久化。
- **Cloudflare Durable Objects** 按 key 持有状态，可跨越数小时或数周。把计算与获批动作的存储放在一起。
- **Microsoft Agent Framework** 在工作流 API 中暴露 `Checkpoint` 原语；replay 加 idempotency 覆盖重试。

在每一种情况下，真正有效的组合都是：idempotency key（防止重复执行）+ precondition check（状态仍是当初获批时的那一份）+ 动作后校验（副作用确实发生了）+ 校验失败时回滚。

## 核心概念

### 每一次转换都会持久化

图状态转换是指把工作流从一个具名状态推进到另一个具名状态的任何一步。朴素实现只在特定的提交点持久化；生产实现会持久化每一次转换。代价（多几次写入）相对于可靠性收益（replay 能落在任意位置、租约恢复精确）很小。

### 租约恢复

worker 崩溃时，工作流并未丢失；租约（一份声明“该 worker 正在执行这次运行”的短时凭据）只是过期了。另一个 worker 取走最新的 checkpoint 并继续。租约机制正是生产系统能在滚动部署中存活而不丢失在途工作的原因。

### 幂等性加前置条件

仅有幂等性是不够的。设想：一个工作流获批“当余额 > $1000 时，从 A 转账 $100 到 B”。工作流已提交，执行中途崩溃，然后恢复。如果只检查 idempotency key，执行恢复后转账只跑一次（正确）。但设想在崩溃与恢复之间，A 的余额经由另一个工作流降到了 $500。idempotency 检查仍然通过；前置条件通不过。没有 precondition check，我们就会发出一笔透支。

每一个有后果的动作都需要两者：

- **Idempotency key**：防止重复执行。
- **Precondition check**：确认状态仍与当初获批的内容一致。

### 动作后校验

“工具返回了 200”不叫校验。真正的校验会重新读取目标状态，确认副作用确实发生了。常见模式：

- 数据库更新：`UPDATE ... RETURNING *`，然后断言返回的行与预期状态一致。
- 发邮件：提交后到已发送文件夹里查消息 ID。
- 写文件：把文件读回来并做哈希。
- API 调用：对目标资源跟一次 `GET`。

如果校验失败，工作流就处在已知的坏状态。回滚启动。

### 回滚方案

propose-then-commit（第 15 课）里每一个有后果的动作都带一份回滚方案。类型：

- **In-band rollback**：直接反转副作用（`INSERT` 之后 `DELETE`，发送之后发一封更正邮件）。
- **Compensating transaction**：用一个新动作中和原动作（标准的 SAGA 模式）。
- **Out-of-band rollback**：告警给人类，暂停工作流，把坏状态留给调查。

No-op rollback（“这个我们撤不回来”）必须在提案里写明。没有回滚的动作在提交时要求更强的 HITL（第 15 课的 challenge-and-response）。

### EU AI Act Article 14 的落地解读

Article 14 要求高风险系统具备“有效的人类监督”。落实到操作层面，实施者的解读是：

- checkpoint 可被审计者查询。
- rollback 经过演练（至少端到端跑通一次）。
- 审计轨迹能在一次部署后存活（checkpoint 后端不是临时的）。
- 校验失败会触发告警，而不是被静默记进日志。

一个在提交中途崩溃、恢复、并在没有校验 + 回滚通路的情况下完成副作用的动作，是过不了 Article 14 这道关的。

### 最尖锐的失效模式：重复执行

这个领域最常见的生产事故：

1. 动作获批，idempotency key 为 k。
2. 提交开始，执行，返回 200。
3. 工作流在持久化“已提交”状态之前崩溃。
4. 工作流恢复；看到“已获批但未提交”；重新执行。
5. 副作用触发两次。

缓解办法：在执行前先持久化一个“in-flight”意图，带 idempotency key 执行，然后仅在动作后校验成功之后才标记“已提交”。如果动作触发了而状态写入失败，你知道要去校验并（如有必要）重新触发。如果状态写入成功而动作失败，你通过恢复路径校验并恰好触发一次。

```figure
checkpoint-replay
```

## Use It

`code/main.py` 实现了一个带 checkpoint 的工作流，包含 idempotency、preconditions、verify 和 rollback。driver 模拟四种场景：干净运行、崩溃后重试（idempotency 拦住）、前置条件失败（工作流中止且不触发）、校验失败（回滚触发）。

## Ship It

`outputs/skill-rollback-rehearsal.md` 为一个拟议工作流设计回滚演练测试，并审计 checkpoint 后端在审计轨迹持久化方面的表现。

## Exercises

1. 运行 `code/main.py`。验证四种场景。对于提交中途崩溃的情形，确认动作在多次重试中恰好触发一次。

2. 修改“先标记完成、再执行”的模式，让状态写入发生在动作之后。重跑崩溃场景。测量重复动作触发了多少次。

3. 为一个具体的生产动作（例如“向某个 Slack 频道发消息”）设计回滚方案。归类为 in-band、compensating 或 out-of-band。说明你选择的理由。

4. 拿一个你熟悉的工作流。找出每一次状态转换。给每一处标注持久化要求（持久化 / 不持久化）。数一数你当前没有持久化的有多少处。

5. 演练式回滚测试：设计一个端到端测试，它会跑一个真实工作流、让它崩溃、并确认回滚通路被触发。这个测试断言什么？

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|---|---|---|
| Checkpoint | “保存点” | 每一次图状态转换都持久化到持久化存储 |
| Lease | “worker 认领” | worker 正在执行某次运行的短时凭据；崩溃时过期 |
| Precondition | “状态闸门” | 断言状态仍与获批动作保持一致 |
| Post-action verify | “回读检查” | 确认副作用确实在目标系统中发生了 |
| In-band rollback | “直接撤销” | 用逆操作反转副作用 |
| Compensating transaction | “SAGA 撤销” | 用一个新动作中和原动作 |
| Mark-as-done-first | “状态写入顺序” | 在从提交返回之前先持久化已提交状态 |
| Article 14 | “EU AI Act 人类监督” | 操作层面：可查询的 checkpoint、演练过的 rollback、可审计的轨迹 |

## Further Reading

- [Microsoft Agent Framework — Checkpointing and HITL](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — checkpoint 原语与租约恢复。
- [Cloudflare Agents — Human in the loop](https://developers.cloudflare.com/agents/concepts/human-in-the-loop/) — 以 Durable Objects 作为状态基底。
- [EU AI Act — Article 14: Human oversight](https://artificialintelligenceact.eu/article/14/) — 监管基线。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 面向长时程工作流的可靠性框架。
- [Anthropic — Claude Code Agent SDK: agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) — Claude Code Routines 的工作流形态。
