---
name: failure-detector
description: 为智能体轨迹生成失败模式检测器，接入一个轨迹存储，标记业界反复出现的五种模式以及领域特定的签名。
version: 1.0.0
phase: 14
lesson: 26
tags: [failure-modes, masft, detection, observability]
---

给定一个产品领域和一个轨迹存储，产出智能体失败模式的检测器。

产出：

1. 每种模式一个检测器：`hallucinated_action`、`scope_creep`、`cascading_errors`、`context_loss`、`tool_misuse`、`success_hallucination`。
2. 领域特定检测器（例如对开发工具而言的「创建 PR 却没有关联 issue」，对营销工具而言的「未经确认就给 >5 个收件人发邮件」）。
3. 一个标注器，把所有检测器应用到每条轨迹并输出分布。
4. 基于阈值的告警：如果今天 >=5% 的轨迹被标记出某种模式，就发 page 或开一张工单。
5. 样本保留：对每条被标记的轨迹，保留输入 + 输出 + 状态快照供操作人员复核。

硬性拒绝：

- 在生产中对每条轨迹都需要 LLM 调用的检测器。使用基于模式的检测器；把 LLM-judge 留给抽样复核。
- 只在崩溃时标记。大多数失败产出的输出看起来都是有效的。必须对内容 + 状态做签名检查。
- 存储被标记的轨迹却不做 PII 脱敏。失败样本承载着最糟糕的内容；存储前先清洗。

拒绝规则：

- 如果用户想要「所有轨迹永久存储」，出于成本和合规原因拒绝。按标签 + 速率抽样。
- 如果产品没有「已知良好」基线，拒绝漂移告警。漂移需要一个参照物。
- 如果检测器没有版本化，拒绝。检测器回归会在你毫无察觉时破坏你的信号。

输出：`detectors.py`、`tagger.py`、`alerts.py`、`retention.py`、`README.md`，说明阈值、保留策略、告警路由。结尾附「下一步读什么」，指向第 24 课（observability backends）或第 27 课（prompt injection）以了解对抗性失败模式。
