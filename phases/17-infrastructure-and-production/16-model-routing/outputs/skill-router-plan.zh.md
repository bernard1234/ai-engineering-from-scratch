---
name: router-plan
description: 设计一份 LLM 模型路由方案——挑选模式（pre-route、cascade、ensemble）、信号（任务、长度、embedding、置信度）与在线质量闸门。
version: 1.0.0
phase: 17
lesson: 16
tags: [routing, cascade, model-cascade, routellm, notdiamond, cost-reduction]
---

给定负载组合（任务分类样本）、质量下限、latency 容忍度与当前每月支出，产出一份路由方案。

产出：

1. 模式。Pre-route（最快，依赖分类器）、cascade（质量下限最好）或 ensemble（仅用于样本 A/B）。用质量容忍度 + latency 预算给出理由。
2. 信号。从以下挑选：任务分类、prompt 长度、与已知困难集的 embedding 相似度、自我置信度。说明组合了哪些（通常是 2-3 个）以及组合规则。
3. 便宜/frontier 配对。点名具体模型。例如：Claude Haiku 3.5 + GPT-5。用成本曲线 + 能力给出理由。
4. 预期节省。在建议切分下计算混合成本；给出预期每月 $ 相对当前的变化。
5. 在线质量闸门。规定实时流量 judge：每条路由采样 5%，由 frontier judge 评估；若 Δ 质量 > 2% 则告警。跟踪升级率；若一个月内攀升 >10 个百分点则告警。
6. 上线节奏。影子（路由但忽略结果；离线对比）、按用户群 10% 灰度、通过闸门后扩量。

硬性拒绝：
- 没有在线质量闸门就做路由。拒绝——漂移是头号失败。
- 只用任务分类作为信号。拒绝——会漏掉任务内部的难度差异。
- 把本应走 frontier 的任务（代码、数学、多步）路由到便宜模型且没有 cascade 兜底。拒绝——质量下限会被击穿。

拒绝规则：
- 如果质量容忍度被表述为“零回归”，拒绝 pre-route，并建议采用高升级率的 cascade。
- 如果便宜模型非 Anthropic/非 OpenAI/非 frontier，且有已知的拒绝模式（例如用于 agent tool-use 的未审查模型），拒绝这一配对——它会悄悄弄坏 tool 调用。
- 如果便宜档路由到不同的 provider（跨 provider cascade），要求使用 AI 网关层（第 17 阶段 · 19）来统一 API。

输出：一页方案，点名模式、信号、模型配对、预期节省、在线闸门、上线计划。最后给出单一指标：滚动 7 天内的升级率；若变化 > 10 个百分点则触发漂移。
