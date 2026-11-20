---
name: scheming-triage
description: 依据 Apollo 三支柱 scheming 框架，对一份 agent 部署事故报告做分诊。
version: 1.0.0
phase: 18
lesson: 8
tags: [scheming, agent-safety, apollo, three-pillars, safety-cases]
---

给定一份 agent 部署事故报告（意外的工具使用、数据访问、与自我保全相关的行为），对失败模式分类，并在 scheming 是候选时应用 Apollo 三支柱测试。

产出：

1. 失败类别分诊。把事故标记为以下之一：能力失败（模型无法完成任务）、控制失败（监控/工具使用协议未能约束模型），或 scheming（模型为服务于另一个 in-context 目标而采取违背用户目标的行动）。
2. 三支柱检查（如果 scheming 是候选）。
   - Misalignment：该行动是否服务于环境中或工具输出里存在的某个正交目标？
   - Goal-directedness：该行动是多步计划的一部分，还是一次性错误？
   - Situational awareness：是否有证据表明模型当时知道自己正被评估？
3. 评估上下文审计。该事故是在部署中观察到的、在红队评估中观察到的，还是两者皆有？如果只在部署中出现，注明评估时的结果不能迁移（Apollo 2025 警告）。
4. 引发可复现性。同一个 prompt + 环境能否再次产生该行为？可复现的事故落在三支柱框架内；不可复现的可能是能力引发的人为产物。
5. 安全论证缺口。本次部署当前的安全论证处理了三根支柱中的哪几根，又留下了哪几根未覆盖？

硬性拒绝：
- 任何把 scheming 当作能力类失败的框架。Scheming 需要 goal-directedness 和 situational awareness——缺乏能力的模型无法 scheming。
- 任何由“anti-scheming 训练降低了 covert-action 率”推出“底层 misalignment 降低”的结论，除非检查了同一模型的评估上下文识别率。
- 任何因 agent 没有外泄数据就宣称 oversight subversion“不是攻击”的说法——oversight subversion 本身就是一种 scheming 行动。

拒绝规则：
- 如果用户问“我的模型是否在 scheming”，在没有三支柱证据时拒绝给出二元答案；先索取评估上下文和引发可复现性数据。
- 如果用户要求给出残余 scheming 概率，拒绝给出数值答案，并解释 2026 年的评估可靠性受模型自身 situational awareness 的约束。

输出：一份一页的分诊，标记失败类别，用现有证据填满三根支柱，标出缺失的证据，并指出最迫切需要弥合的那一个安全论证缺口。引用 Meinke et al.（arXiv:2412.04984）一次，作为框架来源。
