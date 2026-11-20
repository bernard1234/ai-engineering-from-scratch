---
name: load-test-plan
description: 设计一次真实的 LLM 负载测试——选择工具（LLMPerf、k6、GenAI-Perf、guidellm），构建四种模式（steady、ramp、spike、soak），并在 CI 中设 gate。
version: 1.0.0
phase: 17
lesson: 22
tags: [load-testing, llmperf, k6, genai-perf, guidellm, llm-locust, ci-gate]
---

给定工作负载（端点、TTFT/TPOT/error 的 SLA）、目标规模（并发、RPS）以及 CI 姿态（PR gate 还是仅发布时跑），产出一份负载测试计划。

产出：

1. **工具。** 基线运行用 LLMPerf；CI gate 用 k6 + 流式扩展；NVIDIA 参考运行用 GenAI-Perf；大规模合成用 guidellm。只有已经用 Locust 时才用 LLM-Locust。
2. **Prompt 分布。** 输入 token 的均值 + 标准差取自真实流量（若有）或公开分布（ShareGPT / HumanEval）。禁止单 prompt 循环。
3. **四种模式。** Steady、ramp、spike、soak。每种给出：目标 RPS、时长、预期失败模式。
4. **CI gate。** 具体阈值：TTFT P95 < X、5xx < 5%、TPOT < Y。每个 PR 的运行时长：3-5 分钟。
5. **指标口径对齐。** 注明上报工具是 GenAI-Perf 风格（ITL 不含 TTFT）还是 LLMPerf 风格（ITL 含 TTFT）。选一种并保持一致。
6. **产出。** 一个提交进仓库的脚本文件（k6 JS、LLMPerf CLI）。

硬性拒绝：
- 用均一 prompt 做负载测试。拒绝——数字会撒谎。
- 不支持流式的负载测试。拒绝——LLM 端点默认就是流式的。
- 跨工具比较数字却不说明指标定义差异。拒绝。

拒绝规则：
- 如果团队打算用原版 Locust 而不装 LLM-Locust 扩展，拒绝——GIL 陷阱。
- 如果每个 PR 的 CI gate 预算 < 60 秒，拒绝完整 soak——建议一次快速 steady-state 加单独的 nightly soak。
- 如果拿不到 prompt 分布数据，要求使用有记录的公开分布（ShareGPT）并注明该假设。

输出：一页纸的计划，包含工具、prompt 分布、带目标的四种模式、CI gate 阈值、指标口径对齐。最后给出唯一的 CI 输出：仅当所有阈值都满足且连续 3 次稳定时，PR 才变绿。
