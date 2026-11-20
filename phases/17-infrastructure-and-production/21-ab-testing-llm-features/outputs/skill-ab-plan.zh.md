---
name: ab-plan
description: 设计一个 LLM A/B 测试——选择平台（Statsig 或 GrowthBook）、主指标、护栏、带 LLM 噪声缓冲的样本量、CUPED、sequential 停止与多重比较校正。
version: 1.0.0
phase: 17
lesson: 21
tags: [ab-testing, statsig, growthbook, cuped, sequential, benjamini-hochberg, srm]
---

给定功能变更（prompt / model / generation parameter）、基线指标、预期提升，以及团队姿态（warehouse-native OSS 还是打包 SaaS），产出一份 A/B 计划。

产出：

1. **平台。** Statsig（打包 SaaS，OpenAI 旗下）或 GrowthBook（MIT OSS，warehouse-native）。给出理由。
2. **主指标 + 护栏。** 主指标是你想推动的指标；护栏是绝不能回归的东西（cost/request、latency P99、refusal rate）。
3. **样本量。** 经典 power 计算 × 1.4（LLM non-determinism 缓冲）。
4. **设计。** 固定时域或 sequential。预期信号强就用 sequential；变更细微就用固定时域。
5. **CUPED。** 如果主指标有前期数据就启用；指明回归量。
6. **校正。** 少量测试用 Bonferroni；大量相关测试用 Benjamini-Hochberg。
7. **SRM。** 每个实验都必须做 SRM 检查；一旦标记就暂停并排查。

硬性拒绝：
- 靠 vibe 上线。拒绝——要求 A/B，或有记录在案的免 A/B 例外。
- 在同一主指标上跑 >5 个实验却不做 BH/Bonferroni。拒绝——假发现几乎必然。
- 跳过 SRM 检查。拒绝——分配 bug 很常见。

拒绝规则：
- 如果该功能的流量低于 1000 用户/周，拒绝固定时域 A/B——改用 shadow + canary（第 17 阶段 · 20）。
- 如果主指标是主观的（例如“质量”）且没有客观代理，要求并行做人工 eval。
- 如果提升假设小于 LLM 噪声地板，拒绝——实验用现实的样本量检测不到它。

输出：一页纸的计划，包含平台、主指标 + 护栏、样本量、设计、CUPED、校正、SRM 策略。最后给出决策规则：主指标显著 + 所有护栏均未显著变差 → 上线；任一护栏越界 → 无论主指标如何都不上线。
