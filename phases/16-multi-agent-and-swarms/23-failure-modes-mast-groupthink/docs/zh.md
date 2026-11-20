# 失效模式 —— MAST、groupthink、单一文化、级联错误

> 2026 年的参考分类法就是 **MAST**（Cemri 等，NeurIPS 2025，arXiv:2503.13657），它源自 7 个最先进开源 MAS 的 1642 条执行 trace，显示 **41–86.7% 的失效率**。三大根类别：**Specification Problems**（41.77%）——角色含糊、任务定义不清；**Coordination Failures**（36.94%）——沟通中断、状态不同步；**Verification Gaps**（21.30%）——缺少验证、没有质量检查。**Groupthink** 家族（arXiv:2508.05687）补充：单一文化崩塌（同一基座模型 → 相关失效）、从众偏差（agent 互相强化彼此的错误）、心理理论不足、混合动机动态、可靠性级联失效。级联例子：重试风暴，支付失败触发订单重试，订单重试触发库存重试，进而压垮库存服务（数秒内负载 10 倍 —— 需要熔断器）。记忆投毒：一个 agent 的幻觉进入共享记忆，下游 agent 把它当事实；准确率逐渐衰减，使根因诊断极为痛苦。**STRATUS**（NeurIPS 2025）报告，通过专门的检测 / 诊断 / 验证 agent，缓解成功率提升 1.5x。本课把失效模式当作一等工程目标。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** 第 16 阶段，第 13 课（Shared Memory）、第 14 课（Consensus and BFT）、第 15 课（Voting and Debate Topology）
**Time:** ~75 分钟

## 问题场景

多 agent 系统在真实任务上有 41-86.7% 的失效率（Cemri 等 2025 在 7 个开源 MAS 上测得）。这不是"多加几个 agent"就能调试掉的。这些失效有结构性成因。MAST 分类法给了你类别。本课把每个类别映射到一套具体的检测、诊断与缓解模式，让这些数字不再显得随意。

2026 年的生产实践是把失效模式当作设计输入。在你的架构能为每个 MAST 类别指出所用缓解措施之前，它都算不上"足够好"。

## 核心概念

### MAST 类别

**Specification Problems（占失效的 41.77%）。** Agent 的任务定义得不够严密。示例：

- 角色含糊：两个 agent 都以为自己是评审。
- 任务欠明确：用户想要特定视角时，你只说"总结一下"。
- 成功标准隐含：agent 无法判断自己是否成功。

缓解：
- 写显式角色契约。每个 agent 的 prompt 声明它做什么、*以及不做什么*。
- 每个任务配验收测试。在 agent 开始前，定义"完成是什么样子"。
- 派发前做规格预检：由一个独立 agent 在任务下发前审查任务定义。

**Coordination Failures（36.94%）。** 沟通或状态断裂。

示例：
- 两个 agent 不同步地更新共享状态。
- agent 之间消息丢失（queue 故障、超时）。
- 状态漂移：agent A 以为任务完成，agent B 还在执行。

缓解：
- 带版本的共享状态 + 乐观并发控制。
- 关键消息显式确认（未确认则重试）。
- 周期性状态同步 checkpoint，尽早发现漂移。

**Verification Gaps（21.30%）。** 输出没有独立校验。

示例：
- 一个 agent 宣称成功，无人核实。
- agent 链条上每一环都信任上一环的输出。
- 对涌现出的组合行为缺少测试覆盖。

缓解：
- 独立验证器 agent（第 13 课）。只读、独立数据源访问。
- 显式交接契约："B 开始前，A 的输出必须通过检查器 C。"
- 记录结果，便于事后分析。

### Groupthink 家族（arXiv:2508.05687）

agent 同质化或互相模仿时的五种相关失效：

**单一文化崩塌。** 同一基座模型或训练数据 → 相关错误。三个 agent 共用一个 LLM 时，就共享它的幻觉。

**从众偏差。** Agent 向最响亮或最自信的同伴靠拢，即使对方是错的。

**心理理论不足。** Agent 无法为彼此的信念建模，协调随之瓦解（第 18 课）。

**混合动机动态。** 激励部分对齐的 agent 漂向折中中间态，谁都不满意。

**可靠性级联失效。** 一个组件的错误模式触发依赖组件的错误模式。

### 级联示例 —— 重试风暴

一个典型的 2026 年事故模式：

```
payment service fails 10% of requests
   ↓
order agent retries payment (exponential backoff but naive)
   ↓
each retry is a new order-inventory check
   ↓
inventory service sees 2x normal load
   ↓
inventory service starts timing out
   ↓
every order retries inventory check
   ↓
inventory service sees 10x normal load
   ↓
cluster goes down
```

修复是经典手段：**熔断器**。当下游错误率超过阈值，用缓存或默认结果短路。再加上每请求设有上限的重试预算。

熔断器是你几乎无需修改就能从分布式系统直接借来的少数多 agent 失效缓解措施之一。

### 记忆投毒（再谈）

来自第 13 课：一个 agent 的幻觉变成共享记忆里的事实；下游 agent 在这个被投毒的事实上推理。用 MAST 的话说，这是共享记忆层上的验证缺口。

准确率逐渐衰减是症状。你不会看到崩溃，只会看到难以定位根因的缓慢漂移。

缓解：仅追加日志、来源追踪、不可写的验证器。第 13 课已讲过。

### STRATUS —— 用于失效检测的专用 agent

STRATUS（NeurIPS 2025）报告，部署以下三者后缓解成功率提升 1.5x：

- **检测 agent。** 监视症状模式（高分歧、重试尖峰、准确率漂移）。
- **诊断 agent。** 给定症状，从 MAST 分类法推断可能的根因。
- **验证 agent。** 缓解措施应用后，检查症状是否消退。

这是 SRE 风格的事故响应，套用到 agent 系统上。三个角色都可以是带有专用 prompt 的 LLM agent。

### 失效模式审计

2026 年的最佳实践是年度（或每个大版本）失效模式审计：

1. **Trace 采样。** 收集约 1000 条真实执行 trace。
2. **归类。** 对每条 trace 的失效，映射到 MAST + Groupthink 类别。
3. **计算分类失效率。** 哪些类别在你的系统里占主导？
4. **给缓解措施排序。** 哪项修复能消除最多失效？
5. **选 2-3 项缓解。** 实施；下季度重审。

这套纪律比具体选择更重要。没有审计，失效就融进噪声，永远得不到系统性处理。

### 当系统静默失败

最危险的失效类别是静默的正确性失效。响亮失败的系统（崩溃、异常、告警）可以被监控。产出看似合理但错误输出的系统，异常日志抓不到。这就是为什么验证缺口按单次失效算是最贵的类别，尽管按数量只占 21.30%。

投入：
- 基于抽样的人工评审。
- 金标数据集回归测试。
- 对重要输出做跨 agent 交叉核查。

### 失效与慢失效

有些失效是即时的，有些是缓慢的。即时失效（超时、schema 不匹配、鉴权错误）检测成本低。慢失效（记忆投毒、单一文化漂移、角色含糊）检测与预防成本高。

2026 年的工程动作：为慢失效装代理指标，以便在漂移变成显性错误之前抓住它。一致率、重试率、输出长度分布，以及相邻 agent 版本之间的编辑距离，都是有用的代理指标。

```figure
a5-retry-cascade
```

## Build It

`code/main.py` 实现：

- `FailureTaxonomy` —— 把模拟事故归入 MAST + Groupthink 类别。
- `CircuitBreaker` —— 经典模式；错误率超过阈值时打开。
- `RetryStormSimulator` —— 展示级联失效；可开关熔断器。
- `DetectionAgent` —— 脚本化的 STRATUS 风格症状匹配器。

运行：

```
python3 code/main.py
```

预期输出：
- 没有熔断器的重试风暴：库存错误爆炸（模拟）。
- 有熔断器：在阈值处封顶；提供降级模式响应。
- 检测 agent 标出该模式并指出 MAST 类别。

## Use It

`outputs/skill-mast-auditor.md` 对多 agent 系统执行 MAST 风格失效模式审计。Trace → 归类 → 缓解排序。

## Ship It

生产中的失效模式纪律：

- **每季度做 MAST 审计。** 不是每年。类别会随系统成长而迁移。
- **处处熔断器。** 每次对任何依赖服务的外部调用。默认打开阈值设在 5-10% 错误率。
- **金标数据集。** 小、高质量、人工审计过。每周对其做回归测试。
- **STRATUS 三件套。** 检测 + 诊断 + 验证 agent 监控生产。先只上检测 agent；症状噪声大时再加诊断。
- **失效预算。** 按类别为失效率设定显式 SLO。超出预算触发"停止发布"的对话。

## Exercises

1. 运行 `code/main.py`。确认熔断器给重试风暴封顶。改变失败阈值，观察权衡。
2. 实现一个**慢失效代理指标**：3 个并行 agent 之间的一致率。当它急剧下降时触发告警。通过逐步让 agent 输出相关来模拟单一文化漂移。
3. 读 Cemri 等（arXiv:2503.13657）。挑一个他们的 7 个 MAS 系统，映射其前 3 大失效类别。这些与 MAST 的预测相比如何？
4. 读 Groupthink 论文（arXiv:2508.05687）。指出五种模式中哪种在生产中最难检测。提出一个代理指标。
5. 为一个你熟悉的具体多 agent 系统设计 STRATUS 风格的检测-诊断-验证三件套。检测监视哪些症状？诊断推荐哪些缓解？验证如何确认它们有效？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| MAST | "2026 年的分类法" | Cemri 2025；3 大根类别 + 14 个失效子类型。 |
| Specification Problem | "角色含糊" | 任务或角色定义不足；agent 不知道要做什么。 |
| Coordination Failure | "状态漂移" | agent 之间的沟通或同步断裂。 |
| Verification Gap | "没人检查" | 输出未经独立校验就被接受。 |
| Groupthink family | "同质化失效" | 单一文化、从众、ToM 不足、混合动机、级联。 |
| Monoculture collapse | "同一模型，同一幻觉" | 共享基座模型或训练数据导致的相关错误。 |
| Retry storm | "级联错误放大" | 一次失败触发重试，重试放大下游负载。 |
| Circuit breaker | "错误率到就快速失败" | 错误率超阈值时打开；用默认值短路。 |
| STRATUS | "事故响应三件套" | 检测 + 诊断 + 验证 agent。缓解成功率 1.5x。 |
| Memory poisoning | "幻觉传播" | 共享记忆中的事实被污染；下游 agent 在毒上推理。 |

## Further Reading

- [Cemri 等 —— 多 agent LLM 系统为何失败？](https://arxiv.org/abs/2503.13657) —— MAST 分类法，NeurIPS 2025
- [多 agent LLM 中的 Groupthink 失效](https://arxiv.org/abs/2508.05687) —— 单一文化、从众，以及五家族分类法
- [STRATUS —— 用于 MAS 事故响应的专用 agent](https://neurips.cc/) —— NeurIPS 2025 论文集条目（检测 + 诊断 + 验证）
- [Release It! —— 稳定性模式（Nygard）](https://pragprog.com/titles/mnee2/release-it-second-edition/) —— 熔断器的经典参考
- [Anthropic —— 多 agent 研究系统](https://www.anthropic.com/engineering/multi-agent-research-system) —— 生产失效模式笔记
