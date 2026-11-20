# 生产环境中的 EAGLE-3 Speculative Decoding

> Speculative decoding 把快速的 draft 模型与 target 模型配对。draft 提议 K 个 token，target 用一次前向完成验证，被接受的 token 就是白赚的。2026 年，EAGLE-3 是生产级变体 —— 它在 target 模型的隐藏状态而非原始 token 上训练 draft head，把通用聊天场景下的接受率 alpha 推到 0.6-0.8 区间。正确的问题不是“draft 有多快”，而是“我的流量上 alpha 是多少？”如果 alpha 掉到约 0.55 以下，在高并发下 speculative decoding 就是净负收益，因为每个被拒绝的 draft 都要多付一次 target 前向。本课教你先测量 alpha，再翻开关。

**Type:** Learn
**Languages:** Python (stdlib, 玩具级接受率模拟器)
**Prerequisites:** 第 17 阶段，第 04 课（Serving Engine Internals），第 10 阶段，第 18 课（Multi-Token Prediction）
**Time:** ~60 分钟

## Learning Objectives

- 说出 speculative decoding 的三代方案，并解释 EAGLE-3 相对 EAGLE-2 和经典 draft 模型改变了什么。
- 定义接受率 alpha，根据 alpha 与 K（draft 长度）计算预期加速比，并找出目标并发下的盈亏平衡 alpha。
- 解释为什么 2026 年的 vLLM 里 speculative decoding 是可选开启（而非默认），以及为什么不测 alpha 就打开它是生产反模式。
- 写出测量计划：用哪个 benchmark、哪种 prompt 分布、哪个并发点、以哪个指标作为门禁。

## 问题场景

Decode 是内存受限的。在跑 Llama 3.3 70B FP8 的 H100 上，每生成一个 token 都要以约 140 GB/s 读取权重，然后输出一个 token。decode 期间 GPU 计算几乎空闲 —— 瓶颈是 HBM 带宽，而不是矩阵乘吞吐。

Speculative decoding 利用的正是这个空隙。用一个廉价的 draft 模型生成 K 个候选 token，然后让 target 模型在一次前向中验证全部 K 个。每个通过验证的 token 实际上都是白赚的（它被摊薄进 target 本来就要做的一次 K 批前向中）。

经典的 draft 模型方案使用同家族的较小模型（用 Llama 3.2 1B 为 Llama 3.3 70B 做 draft）。它能用，但接受率平平 —— 小模型的分布会偏离 target。EAGLE、EAGLE-2、EAGLE-3 则直接在 target 模型的内部状态上训练一个轻量 draft head，因此 draft 的分布能更紧密地跟随 target。这就是为什么 alpha 能从 draft 模型的 0.4 提升到 EAGLE-3 的 0.6-0.8。

问题在于：2026 年的 vLLM 中 EAGLE-3 需要显式开启。必须显式设置 `speculative_config`。没有这个开关，就没有加速。那些不测真实流量上的 alpha 就打开它的团队，往往会发现尾部延迟变差而不是变好。

## 核心概念

### Speculative Decoding 到底买到了什么

没有 spec decode 时，每个 token 的代价是一次 target 前向。开启 spec decode、draft 长度为 K、接受率为 alpha 时，每次 target 前向的期望 token 数为 `1 + K * alpha`。加速比为 `(1 + K * alpha) / (1 + epsilon)`，其中 epsilon 是 draft 加验证的开销。对 K=5、alpha=0.7：`(1 + 5*0.7) / (1 + 0.1) = 4.5 / 1.1 = 4.1x`。真实世界的数字大多落在 2-3 倍，因为生产流量上的 alpha 很少有那么高，而 epsilon 会随 batch size 增大而上升。

### 为什么 alpha 是唯一重要的指标

被拒绝的 token 不会凭空消失 —— 它们会迫使 target 为第一个被拒绝的 token 再做一次前向。在 alpha 掉到 0.4 的负载上，你要付 draft 开销、验证开销，还要重抽。在高并发下（比如 256 并发），decode 批次已经足够大，以至于“只有 target”和“target 加验证”之间的内存带宽差距会缩小。在 2026 年的大多数硬件上，alpha 低于 0.55 时 spec decode 就是净负收益。

alpha 因负载而异。在 ShareGPT 风格的通用聊天上，用 ShareGPT 训练的 EAGLE-3 能到 0.6-0.8。在领域特定流量（代码、医疗、法律）上，用通用数据训练的 draft head 会掉到 0.4-0.6。训练一个领域特定的 draft head 可以把 alpha 找回来 —— 与 target 微调相比，这是一项轻量、快速的训练任务。

### EAGLE 各代速览

- **经典 draft 模型**：同家族的较小模型。alpha 0.3-0.5。基础设施简单 —— 加载两个模型，每次 target 前向时 draft 跑 K 次前向。
- **EAGLE-1（2024）**：在 target 隐藏状态（最后一层）上训练的单一 draft head。alpha 约 0.5-0.6。在 target 之上只增加很少的参数。
- **EAGLE-2（2025）**：自适应 draft 长度与树状 draft（在一次 target 前向中验证多个分支）。alpha 约 0.6-0.7。draft 调度器更复杂。
- **EAGLE-3（2025-2026）**：在 target 的多个层（不只是最后一层）上训练 draft head，对齐更好。通用聊天上 alpha 约 0.6-0.8。

### 2026 年的生产配方

1. 先以裸 target 模型上线。测量目标并发下的基线 TTFT、ITL、吞吐。
2. 通过 vLLM 的 `speculative_config` 启用 EAGLE-3 draft。重新跑 benchmark。
3. 记录接受率 alpha。vLLM V1 以 `spec_decode_metrics.accepted_tokens_per_request` 的形式上报。除以请求的 draft 长度即得 alpha。
4. 如果生产流量分布上的 alpha < 0.55，就关闭 spec decode，或训练一个领域特定的 EAGLE-3 draft。
5. 在生产并发下重跑。确认 P99 ITL 没有变差。

### 生产陷阱：P99 尾部

开启 spec decode 后 ITL 均值会下降。如果不调优，P99 反而可能变差。被拒绝的 draft 会触发两趟序列（draft + 验证失败 + 重抽）。在满批次下，这两趟是串行的。要看 P99 ITL，而不是 P50。

### EAGLE-3 已在哪些地方部署

Google 在 2025 年把 speculative decoding 部署到了 AI Overviews（质量不变，响应更快）。vLLM V1 把 `speculative_config` 作为有文档的接口提供，其特性矩阵把 speculative decoding 标记为与 chunked prefill 兼容。SGLang 支持 EAGLE-3，并把它作为前缀密集型负载推荐的 draft 路径。

### 一行搞定的盈亏平衡数学

预期加速比：`S(alpha, K) = (1 + K*alpha) / (1 + verify_overhead)`。令 `S = 1` 解出 alpha：`alpha_breakeven = verify_overhead / K`。对典型的 verify_overhead ~0.15 与 K=5：`alpha_breakeven = 0.03`。但这只是裸 decode 的数学。在高并发下验证开销会上升，而 decode 批次本已在多个序列间摊薄了内存读取，因此实践中有效的 alpha_breakeven 会升到约 0.45-0.55。

### 什么时候不要用 Speculative Decoding

- 延迟无关紧要的 Batch-1 离线生成。用裸 target。
- 极短的输出（50 token 以下）。draft 开销和验证成本会占主导。
- 没有领域训练 draft head 的垂直领域。alpha 太低。
- 假定任意特性组合都能叠加。对照你的 vLLM 版本检查兼容性矩阵：v0.18.0 把 speculative decoding 标记为与 chunked prefill 兼容。

```figure
mx-speculative-tree
```

## Use It

`code/main.py` 在多种 alpha 取值与 draft 长度 K 下，模拟有和没有 speculative decoding 的 decode 循环。它会打印盈亏平衡 alpha、实测加速比和尾部行为。用若干 (alpha, K) 组合运行它，看看 speculative decoding 究竟在哪里不再划算。

## Ship It

本课产出 `outputs/skill-eagle3-rollout.md`。给定 target 模型、流量分布描述和目标并发，它会产出一份分阶段的 EAGLE-3 上线计划 —— 基准测试、启用配置、测量 alpha、以 alpha >= 0.55 作为门禁、盯住 P99 ITL。

## Exercises

1. 运行 `code/main.py`。在 K=5 时，2 倍加速需要多大的 alpha？3 倍呢？它对 verify_overhead 有多敏感？
2. 假设生产流量中 70% 是通用聊天、30% 是代码。通用聊天在 ShareGPT 训练的 EAGLE-3 下 alpha 为 0.7，代码只有 0.4。混合后的 alpha 是多少，spec decode 是否净收益为正？
3. 阅读 vLLM 的 `speculative_config` 文档。说出三种模式（draft model、EAGLE、N-gram），并核对在你的 vLLM 版本里它们各自能与哪些特性组合。
4. 启用 EAGLE-3 后你看到 ITL 均值下降 25%，但 P99 ITL 上升了 15%。诊断原因并提出缓解方案。
5. 计算 Llama 3.3 70B 上 EAGLE-3 draft head 的内存开销。它和用 Llama 3.2 1B 作为经典 draft 相比如何？

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| Speculative decoding | “draft 加验证” | 用廉价模型提议 K 个 token，在一次 target 前向中验证全部 K 个 |
| Acceptance rate alpha | “spec 接受率” | target 接受的 draft token 比例；唯一重要的指标 |
| Draft length K | “spec k” | 每次 target 前向中 draft 提议多少个 token；通常 4-8 |
| Verify overhead epsilon | “spec 开销” | 相比裸 target 前向，验证并重抽的额外成本；随 batch 增大 |
| EAGLE-3 | “最新 EAGLE” | 2025-2026 变体；在 target 的多个层上训练 draft head；通用聊天上 alpha 0.6-0.8 |
| `speculative_config` | “vLLM spec 配置” | vLLM V1 中显式的可选开启项；没有默认值即没有加速 |
| N-gram spec decode | “N-gram draft” | GPU 侧利用 prompt 中 N-gram 查找的 draft；兼容 chunked prefill |
| Break-even alpha | “无收益 alpha” | spec decode 加速为零时的 alpha；在生产并发下要盯住它 |
| Rejected-draft two-pass | “重抽成本” | draft 被拒时的两次 target 前向；决定 P99 尾部 |

## Further Reading

- [vLLM —— Speculative Decoding 文档](https://docs.vllm.ai/en/latest/features/spec_decode/) —— 关于 V1 中 `speculative_config` 与 chunked prefill 兼容性的权威来源。
- [vLLM Speculative Config API](https://docs.vllm.ai/en/latest/api/vllm/config/speculative/) —— 确切的字段集合。
- [EAGLE 论文（arXiv:2401.15077）](https://arxiv.org/abs/2401.15077) —— 最初的 EAGLE draft head 形式化。
- [EAGLE-2 论文（arXiv:2406.16858）](https://arxiv.org/abs/2406.16858) —— 自适应 draft 与树。
- [UC Berkeley EECS-2025-224](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2025/EECS-2025-224.html) —— 带 speculative decoding 的高效 LLM 系统。
- [BentoML —— Speculative Decoding](https://bentoml.com/llm/inference-optimization/speculative-decoding) —— 生产上线检查清单。
