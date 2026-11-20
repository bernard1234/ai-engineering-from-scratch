---
name: chaos-plan
description: 设计一套 LLM chaos engineering 计划 —— 校验前置条件、搭建四个平面、挑选工具、从三个安全实验起步、强制执行 safety 平面闸门。
version: 1.0.0
phase: 17
lesson: 24
tags: [chaos-engineering, litmuschaos, chaosmesh, harness, llm-chaos, game-day]
---

给定技术栈（Kubernetes / VM / 托管）、SLI/SLO 成熟度、可观测性质量与团队 on-call 成熟度，产出一份 chaos 计划。

产出：

1. 前置条件检查。确认已定义 SLI/SLO、已接好可观测性、已自动化回滚、runbook 已结构化、有 on-call 轮值。若有缺失，拒绝运行生产 chaos。
2. 四个平面。为每个平面（control、target、safety、observability）点名工具。可观测性指向 Phase 17 · 13。
3. 三个初始实验。从 pod kill 起步。然后是供应商 429。再然后是内存过载。每个都要有 blast-radius 上限、时长、成功标准。
4. 安全闸门。Burn-rate（> 期望的 2 倍）、blast-radius（< 车队的 30%）、trace-ID 打标、抑制窗口。
5. 节奏。每周小规模 canary。每月 game day（跨团队）。每季度韧性审计。
6. 工具。LitmusChaos（开源，CNCF 毕业）、Chaos Mesh（开源，CNCF sandbox）、Harness Chaos（商业 AI 辅助）、AWS FIS / Azure Chaos Studio（托管云原生）。

硬性拒绝：
- 在缺少五个前置条件的情况下在生产运行 chaos。拒绝 —— 会变成真实故障。
- 没有 blast-radius 上限的实验。拒绝。
- 没有 trace-ID 打标的实验。拒绝 —— 无法对告警去重。

拒绝规则：
- 如果团队从未在预发成功跑过一个实验，拒绝生产 chaos，直到预发有一个变绿。
- 如果事故量已经很高（> 每周 2 起），拒绝新增 chaos —— 先稳定下来。
- 如果团队没有 SLO，在做任何实验前先要求 SLO。

输出：一页纸的计划，包含前置条件检查、四平面工具、三个初始实验、安全闸门、节奏。结尾用一个每季度更新依赖图的承诺收尾。
