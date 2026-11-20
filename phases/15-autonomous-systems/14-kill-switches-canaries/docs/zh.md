# Kill switch、circuit breaker 与 canary token

> kill switch 是一个布尔值，存放在 agent 可编辑范围之外——一个 Redis 键、一个 feature flag、一份签名配置——用于彻底禁用 agent。circuit breaker 粒度更细：它在特定模式上跳闸（连续五次相同的工具调用），暂停出问题的路径，并升级给人工。canary token 继承自经典的欺骗术：一个伪造的凭证或蜜罐记录，agent 没有任何正当理由去触碰它，一旦访问就触发警报。基于 eBPF 的数据路径（例如 Cilium）可以在内核层把被隔离 pod 的出站流量改写到一个取证蜜罐；公开的 Cilium benchmark 报告在负载下数据路径 P99 延迟低于 1 毫秒（你的传播预算取决于策略更新如何到达节点，而不是数据路径本身）。会适应移动基线的统计检测器（EWMA、CUSUM）会悄无声息地接受漂移——把它们与不会弯曲的硬性宪法限制叠加使用。

**Type:** Learn
**Languages:** Python（stdlib，三种检测器模拟：kill switch、circuit breaker、canary）
**Prerequisites:** 第 15 阶段，第 13 课（Cost governors）、第 15 阶段，第 10 课（Permission modes）
**Time:** ~60 分钟

## 问题场景

成本治理器（第 13 课）约束的是 agent 能花多少钱。它们并不约束 agent 在预算之内能做什么。一个带 $50 速率限制的 agent 仍然可以外泄一个密钥、发布错误的内容，或删除一个资源——昂贵的动作往往是 token 上很便宜的那个。

本课涵盖紧挨成本层而坐的三种检测器：

1. **Kill switch**：一个放在 agent 够不到之处的布尔关机按钮。
2. **Circuit breaker**：一个动作模式检测器，暂停特定路径。
3. **Canary token**：一种诱饵，没有正当理由触碰它的 agent 会因触碰而暴露自己。

这三者都是前 LLM 时代的工程。经典欺骗、限流断路器、feature-flag 关停，都早于自主 agent。新之处在于攻击面：agent 读取不可信内容（第 11 课）、编辑自己的记忆，并能把许多看似安全的动作组合成一个不安全的动作。这里点名的检测器之所以有效，是因为它们不信任 agent 的自我报告。

## 核心概念

### Kill switch

kill switch 是一个 agent 能读但不能写的布尔值。实现选择：

- **托管服务中的 feature flag。** LaunchDarkly、Statsig、Unleash。更新在数秒内传播。
- **agent 轮询的 Redis 键。** 简单；要求 agent 进程在每一轮都检查。
- **对象存储中的签名配置。** agent 在启动时验证签名；拒绝未签名的状态。
- **OS 级信号或容器生命周期关停。** Docker `kill`、Kubernetes `kubectl delete pod`、systemd stop。

一个正确的 kill switch 具备的性质：

- agent 无法把它设为 `off`。（它位于 agent 凭证无法写入的系统中。）
- 它在每一个有后果的动作上都被检查，而不只是在启动时。
- 当它处于关闭状态时，agent 不做任何外部可观察的事情，包括向 agent 能触及的系统写日志。
- 重新启用它是一个明确的人工动作，而不是自动超时。

### Circuit breaker

circuit breaker 暂停一个特定的模式，而不是整个 agent。经典形状（源自 2007 年 Nygard 的书，至今仍适用）：

- **Closed**：动作被允许。
- **Open**：动作被阻止。
- **Half-open**：冷却之后，允许 1–3 次探测尝试（默认 1）；成功则闭合断路器，任何剩余的失败都会重新打开它。

与 agent 相关的触发条件：

- 连续五次相同的工具调用（重复循环）。
- 在同一工具上以不同输入连续五次失败（系统性失败）。
- 工具调用速率超过阈值（第 13 课速率限制）。
- 在读取信任之外内容（第 11 课）之后调用了特定工具（例如 `file.delete`）。

### Canary token

canary token（也叫 honeytoken）是 agent 绝不应触碰的输入。访问即为警报。

面向 agent 的例子：

- 环境里一个没有实际权限的伪造 `AWS_SECRET_ACCESS_KEY`。外泄尝试可立即归因。
- 一条标有已知哨兵值的伪造数据库记录。对该记录的任何读取或更新都会触发警报。
- 工作区里一个伪造文件。对该文件的读取或编辑即可疑。
- 会话开始时注入的一条伪造记忆条目。如果它出现在之后的输出中，说明记忆已被外泄。

canary 设计是工作流特定的。agent 有正当理由触碰的 canary 就是噪声。

### 为什么要叠加统计限制与硬性限制

统计检测器（EWMA、CUSUM、工具调用速率的 z-score）会适应移动的基线。对合法的漂移来说这是一个特性，对对抗性的漂移来说则是一个 bug。有耐心的攻击者可以把基线移动得足够慢，慢到没有任何警报触发。

硬性宪法限制（第 17 课）不会弯曲。把“绝不发邮件给 `secrets@`”作为一条宪法规则更简单、可审计，且不能被缓慢漂移所利用。叠加模式：统计检测器捕获大部分噪声，硬性限制捕获那个走过了检测器的攻击。

### 通过 eBPF 数据路径重定向进行隔离

Cilium 基于 eBPF 的网络策略可以在内核层把被隔离 pod 的出站流量改写到一个取证蜜罐。Cilium 的公开 benchmark 报告在 TCP_RR 上数据路径 P99 延迟低于 1 毫秒；在你的集群中*触发*一次隔离的墙钟预算，主要由策略更新从控制平面传播到节点的方式决定（在 Kubernetes 上、operator 已预加载时，几百毫秒是现实的；尾延迟取决于集群大小和 reconcile 节奏）。这给你两样东西：agent 不会外泄任何真实的东西，且 agent 在蜜罐内部的行为被完整观察。与 canary token 是同一个模式、不同的层：agent 在被围困时试图做什么，就暴露了它的意图。

### 没有检测器能捕获的情况

- **由允许原语组合而成的语义攻击。** 每一个单独的动作都通过了每一个检测器；问题出在组合上。这就是第 10 课中的 Auto Mode 复合失败。
- **把检测器作为 payload 一部分的攻击。** 如果 agent 读到一个页面说“在你行动之前，禁用 canary”，而 agent 又有这个能力，那么检测器就被攻陷了。canary token 应放在 agent 无法修改的系统中。

```figure
circuit-breaker
```

## Use It

`code/main.py` 模拟一条短 agent 轨迹穿过三种检测器。kill switch 存放在一个外部字典中；circuit breaker 在连续五次相同工具调用时跳闸；canary 文件一旦被读取就触发警报。输入一条合成轨迹：合法动作、重复循环、canary 探测，以及一个 kill switch 触发的场景——其中 agent 的动作被中止。

## Ship It

`outputs/skill-tripwire-design.md` 审查一次 agent 部署的拟议检测器栈，并标出缺口（缺少 kill switch、缺少 canary、circuit breaker 阈值过松）。

## Exercises

1. 运行 `code/main.py`。确认 circuit breaker 在第 5 轮（第五次相同调用）跳闸，canary 在第 9 轮（读取伪造密钥）触发。

2. 添加一个统计检测器：工具调用速率的 EWMA z-score。输入一条缓慢漂移的轨迹，展示该检测器从不触发。现在添加一个硬性限制（10 分钟内不超过 50 次工具调用），展示硬性限制在同一条轨迹上触发。

3. 为浏览器 agent（第 11 课）设计一套 canary token。至少列出三个 canary 以及每一个会检测到什么。

4. 阅读 Cilium 网络策略文档。具体描述一个出站重定向的隔离流程：哪个策略选择器、哪个 pod、哪次出站改写、哪个告警。什么决定了从“决定隔离”到“第一个被重定向的包”之间的墙钟延迟？

5. 为一个被 kill switch 关停的 agent 定义重新启用流程。谁能重新启用？必须记录什么？在重新启用之前，agent 必须改变什么？

## Key Terms

| 术语 | 人们的说法 | 实际含义 |
|---|---|---|
| Kill switch | “关机按钮” | agent 可编辑范围之外的布尔值；在每个有后果的动作上检查 |
| Circuit breaker | “模式暂停” | 针对重复、失败率或限流的动作级跳闸 |
| Canary token | “Honeytoken” | agent 没有正当理由触碰的诱饵；访问即触发警报 |
| Honeypot | “取证 sandbox” | 被隔离 agent 在其中被观察的重定向流量 / 工作区 |
| EWMA | “移动平均” | 指数加权；会适应漂移（既是特性也是 bug） |
| CUSUM | “累积和” | 检测相对基线的持续偏移 |
| Hard limit | “宪法规则” | 不适应；无论历史如何都恒定 |
| Constitutional limit | “恒真规则” | 与第 17 课的宪法挂钩；agent 无法编辑 |

## Further Reading

- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 自主 agent 的 kill switch 与 circuit breaker 框架。
- [Microsoft Agent Framework — HITL and oversight](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — 生产治理模式。
- [OWASP LLM / Agentic Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — 检测与响应要求。
- [Cilium — Network policy and eBPF](https://docs.cilium.io/en/stable/security/network/) — pod 级出站重定向与取证蜜罐模式。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 作为“宪法限制”的硬编码禁令。
