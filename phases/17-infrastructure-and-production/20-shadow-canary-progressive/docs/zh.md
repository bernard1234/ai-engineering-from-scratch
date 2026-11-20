# LLM 的 Shadow Traffic、Canary 发布与渐进式部署

> LLM 发布糅合了软件部署中最难的部分：没有单元测试、失败模式模糊、信号滞后。顺序是（1）shadow mode——把生产请求复制给候选模型，记录日志并与生产对比，对用户零影响；它能发现明显的分布问题，但不是质量保证；（2）canary 发布——流量逐步迁移 10% → 25% → 50% → 75% → 100%，每一步都设 gate；跟踪延迟分位数、cost/request、error/refusal 率、输出长度分布、用户反馈率；（3）稳定性确认后，对真正不同的备选方案做 A/B 测试。non-determinism 不可消除——由于 GPU 浮点非结合性加上 batch size 波动，相同输入的多次运行准确率最多可差 15%。成本是变量而非常量——一个好 20% 的模型，每次调用可能贵 3 倍。回滚速度是决定性的：如果回滚需要重新部署，你就太慢了。策略放在 config/flags 里；模型放在 registry 里并固定 digest；回滚 = 翻转策略 + 还原阈值 + 固定旧模型，几秒完成。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级 canary 推进模拟器)
**Prerequisites:** 第 17 阶段，第 13 课（Observability）、第 21 课（A/B Testing）
**Time:** ~60 分钟

## Learning Objectives

- 区分 shadow mode（零影响的对比）、canary（真实流量的渐进迁移）与 A/B（稳定性确认后的对比）。
- 列举五个 LLM 特有的 canary 指标（latency、cost/request、error/refusal、output length 分布、用户反馈）。
- 解释为什么 LLM 的 non-determinism（最高 15%）改变了发布中“稳定”的含义。
- 设计一条几秒完成（翻转策略）、而非几小时（重新部署）的回滚路径。

## 问题场景

你上线了一个新模型。离线 eval 显示准确率提升 3%。你在生产里开了它。24 小时内，成本上涨 40%，用户点踩上涨 8%，三张客户工单都说“回答很怪”。你回滚。重新部署花了 3 小时。你的周末毁了。

这一切本来都可以避免。shadow mode 会在任何用户看到之前就抓到 40% 的成本飙升。canary 会在 10% 时因点踩变化而停下。策略 flag 回滚只需 30 秒。这套纪律正是用来填补“离线 eval 看起来不错”和“真实用户满意”之间的空隙。

## 核心概念

### Shadow mode

候选模型收到与生产相同的请求；输出只记录日志，不返回给用户。零用户影响。记录：

- 输出内容（与生产做 diff）。
- token 数（成本差）。
- Latency。
- 拒绝与错误。

能抓到：成本爆炸、长度回归、明显的拒绝变化、硬错误。抓不到：用户能感知到的质量差异。shadow 是冒烟测试，不是质量测试。

### Canary 发布

带 gate 的渐进式流量迁移。典型推进：1% → 10% → 25% → 50% → 75% → 100%。每一步用 5 个指标把关：

1. **Latency 分位数**——P50、P95、P99。越界：canary 的 P99 > 基线的 1.5 倍。
2. **每请求成本**——混合 $。越界：高于基线 20%。
3. **Error / refusal 率**——5xx 加上显式拒绝。越界：基线的 2 倍。
4. **输出长度分布**——均值 + P99。越界：分布漂移。
5. **用户反馈率**——点踩 / 提交工单。越界：基线的 1.5 倍。

### Non-determinism 是新的方差来源

相同输入会产生不完全相同的输出。原因：

- GPU 浮点运算不满足结合律（浮点归约顺序随 batch 变化）。
- Batch size 波动（同一 prompt 在 batch 128 与 batch 16 中不同）。
- 采样（temperature > 0）。

实测：在相同 eval 集上，run-to-run 准确率波动最高可达 15%。发布语境下的“稳定”指指标落在预期方差内，而不是与基线完全相同。把 gate 设在噪声地板之上。

### 成本是一个变量

一个好 20% 的模型，每次调用可能贵 3 倍。cost/request 是五道 gate 之一。上线一个“更好”但破坏单位经济性的模型，属于回滚场景。

### 回滚是武器

- Policy flag（feature flag 系统）：在配置里翻转比例；耗时数秒。
- Model pinning（registry digest）：被固定的模型不会自动升级。
- 回滚 = 还原 flag + 把固定的 digest 指回上一个。数秒，而不是数小时。

如果你的技术栈回滚需要重新部署，先在发布前修好这一点。

### 工具

**Argo Rollouts** / **Flagger**——Kubernetes 渐进式交付控制器。与 Istio/Linkerd 的加权路由集成。

**Istio weighted routing**——service-mesh 层的流量切分。

**KServe / Seldon Core**——内置 canary 的模型服务。

**Feature flags**——LaunchDarkly、Flagsmith、Unleash。策略层翻转，无需重新部署。

### 指标采集节奏

canary gate 依据流量大小每 5-15 分钟检查一次。1% 流量、每分钟 10 个请求，每个窗口只有 50-150 个数据点——latency 够用，但对用户反馈来说噪声太大。10% 大约多出 10 倍。每级推进都应停留足够久，以积累足够样本。

### A/B 这一步是可选的

如果新模型有本质不同（行为不同、成本曲线不同、语气不同），在 canary 通过后于 50% 做 A/B。若它只是改进版，canary gate 一通过就直接到 100%。

### 你应该记住的数字

- Canary 推进：1% → 10% → 25% → 50% → 75% → 100%。
- Non-determinism 上限：相同输入 run-to-run 波动最高 15%。
- 五个 canary 指标：latency、cost、error/refusal、output length、用户反馈。
- 成本 gate：高于基线 20% 即越界。
- 回滚：数秒，而非数小时。

```figure
i4-canary-ramp
```

## Use It

`code/main.py` 模拟带有注入回归的 canary 发布。报告发布在哪个阶段停止，以及是哪道 gate 触发。

## Ship It

本课产出 `outputs/skill-rollout-runbook.md`。给定候选模型、基线和风险容忍度，设计 shadow→canary→100% 计划。

## Exercises

1. 运行 `code/main.py`。注入 25% 的成本回归。canary 会在哪一阶段停止？
2. 你的新模型离线准确率高 3%，但 cost/request 是 +18%。该不该上线？取决于策略——把两条路径都写出来。
3. 设计一个端到端 60 秒内完成的回滚。列出所需的基础设施。
4. Non-determinism 在你的 eval 上表现为 ±7%。设置 canary gate 以免误报。你用什么乘数？
5. Shadow mode 在 canary 之前就捕获了 40% 的成本飙升。写出在 shadow 阶段触发的告警规则。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Shadow mode | “复制给新模型” | 零影响地发给候选模型并记录 |
| Canary | “渐进流量” | 逐级向用户暴露、带 gate 的发布 |
| Gates | “发布检查” | 阻止推进的指标阈值 |
| Non-determinism | “LLM 波动” | 不可消除的 run-to-run 差异 |
| Policy flag | “翻 flag 回滚” | 配置级回滚，数秒而非数小时 |
| Model pin | “registry digest” | 对某个模型版本的不可变引用 |
| Argo Rollouts | “K8s 渐进发布” | Kubernetes 原生的 canary/回滚控制器 |
| KServe | “推理 K8s” | 带 canary 原语的模型服务 |
| Istio weighted | “mesh 切流” | service-mesh 流量切分器 |

## Further Reading

- [TianPan — Releasing AI Features Without Breaking Production](https://tianpan.co/blog/2026-04-09-llm-gradual-rollout-shadow-canary-ab-testing)
- [MarkTechPost — Safely Deploying ML Models](https://www.marktechpost.com/2026/03/21/safely-deploying-ml-models-to-production-four-controlled-strategies-a-b-canary-interleaved-shadow-testing/)
- [APXML — Advanced LLM Deployment Patterns](https://apxml.com/courses/mlops-for-large-models-llmops/chapter-4-llm-deployment-serving-optimization/advanced-llm-deployment-patterns)
- [Argo Rollouts docs](https://argo-rollouts.readthedocs.io/)
- [Flagger docs](https://docs.flagger.app/)
