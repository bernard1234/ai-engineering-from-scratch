---
name: slo-goodput-gate
description: 产出一份可直接用于 CI/CD 的 benchmark 配方，以 goodput 而非吞吐作为 LLM 部署门禁，附带 P50/P90/P99 百分位和明确的工具选择。
version: 1.0.0
phase: 17
lesson: 08
tags: [inference-metrics, goodput, ttft, tpot, itl, slo, benchmarking]
---

给定负载（模型、硬件、目标并发、面向用户的交互类型 —— 流式聊天 / 单次问答 / 语音 / agent），为 CI/CD 产出一套基于 goodput 的 SLO 门禁。

产出：

1. SLO 规格。三个阈值：TTFT P99 上界、TPOT P99 上界、E2E P99 上界。按交互类型选择站得住脚的值（流式聊天：TTFT 500 ms，TPOT 25 ms，E2E 3 s；语音：TTFT 收紧到 300 ms；agent：E2E 放宽到 5 s）。
2. Benchmark 配方。工具选择（LLMPerf 或 GenAI-Perf —— 说明你选哪个及原因）。Prompt 分布（输入与输出 token 的均值 + 标准差）。并发扫描（目标并发的 25%、50%、100%、150%）。
3. Goodput 计算。公式：同时满足全部三个约束的请求占比。生产目标 >= 99%，canary 目标 >= 95%。
4. 百分位报告。对每个指标报告 P50、P90、P99（绝不只报均值）。均值只作为合理性检查附注。
5. 工具陷阱说明。说明该工具在 ITL 中是否包含 TTFT。在跨团队比较之前先固定定义。
6. 门禁逻辑。在目标并发下 goodput >= 目标值则 CI 通过。若 goodput 在 100% 到 150% 并发之间下降超过 5 个点，标注出来 —— 说明缺少压测余量。

硬性拒绝：
- 只按吞吐设门禁。拒绝，必须用 goodput。
- 只报均值不报 P99。拒绝。
- 省略工具名和工具版本。拒绝。
- 只在目标并发上做 benchmark；永远要做并发扫描。

拒绝规则：
- 如果用户没有写下 SLO，拒绝，先根据交互类型写一个。
- 如果 prompt 分布是“循环发送相同 prompt”，拒绝 —— 这是 prompt 同质化陷阱。要求贴近真实的合成流量。
- 如果 benchmark 少于 30 轮或每轮少于 100 个请求，拒绝，视作统计上不充分。

输出：一页 SLO 门禁规格，列出阈值、benchmark 配方、工具选择、百分位报告模板以及 CI 通过/失败规则。最后用一段“接下来测什么”，根据已知短板点名 goodput 对并发曲线、prompt 分布敏感度或 chunked-prefill 开关的尾部对比之一。
