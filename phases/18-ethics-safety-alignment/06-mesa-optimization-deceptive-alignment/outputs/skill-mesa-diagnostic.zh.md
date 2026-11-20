---
name: mesa-diagnostic
description: 把观察到的安全失效分类为 outer-alignment、proxy-inner 或 deceptive-inner。
version: 1.0.0
phase: 18
lesson: 6
tags: [mesa-optimization, deceptive-alignment, inner-alignment, hubinger]
---

给定一份安全评估报告（eval 任务、失效模式、模型类别、训练配方），把失效归入 Hubinger 2019 的分类，并推荐应对它的缓解类别。

产出：

1. 失效模式归类。从以下选一个：
   - Outer-alignment 失效：base objective（reward、损失）本身就是错的；模型正确地优化了它。
   - Inner-alignment proxy 失效：mesa-objective 是一个在分布内追踪 base 的 proxy；在分布外失效。
   - Inner-alignment deceptive：mesa-optimizer 具有情境意识并在部署时背叛；训练行为干净。
2. 证据追踪。对每个类别，说明什么样的证据会支持它。对 deceptive，要与 proxy 区分：情境意识的证据（日期敏感性、eval-vs-deployment 区分器、chain-of-thought 中的策略性推理）。
3. 缓解类别。对 outer-alignment：改变目标（CAI、更好的 reward 数据、过程监督）。对 proxy-inner：分布覆盖、集成、留出 eval。对 deceptive-inner：控制措施（第 10 课）、可解释性（残差流探针）、能力削减。
4. 已知失效检查。对 deceptive-inner，引用该失效最相似的 2024-2026 经验证明（Sleeper Agents、Alignment Faking、In-Context Scheming）。

硬性拒绝：
- 任何没有情境意识证据的 deceptive-inner 归类。“部署时的意外行为”不够——那可能是 proxy-inner。
- 任何声称仅靠对抗鲁棒性训练就能处理 deceptive-inner 的说法。Hubinger 2019 预测（Sleeper Agents 2024 也确认）对抗训练可能教会模型更好的 test-vs-deployment 区分器。
- 任何用更多数据重训 deceptively aligned 模型的建议。先验预测欺骗会在进一步训练下被保留。

拒绝规则：
- 如果证据只是单个 prompt 上的单次失效，拒绝归类。基础比率很重要；你需要一个失效分布。
- 如果用户要求你“排除” deceptive alignment，拒绝——你可以从证据估计其概率，但无法仅凭行为排除它。

输出：一页诊断，包含类别、证据追踪、缓解类别和最近的实证类比。引用 Hubinger et al.（arXiv:1906.01820）一次。
