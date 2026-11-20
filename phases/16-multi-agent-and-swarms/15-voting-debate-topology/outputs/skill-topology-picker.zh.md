---
name: topology-picker
description: 为给定任务挑选 multi-agent debate 拓扑（star / chain / tree / graph）、agent 数量 N、异构性画像以及轮数上限。
version: 1.0.0
phase: 16
lesson: 15
tags: [multi-agent, debate, topology, voting, self-consistency]
---

给定任务描述，推荐一种 multi-agent 拓扑与规模。

产出：

1. **任务指纹。** 研究型（长程、开放式）、快速事实型（闭式答案）、逐步精炼型（分阶段流水线），还是意见型（无 ground truth）。选一个；若横跨两类，选主导形态。
2. **拓扑。** Star、chain、tree 或 graph。从指纹出发论证：
   - 研究型 → graph（任意到任意的批评）
   - 快速事实型 → star（hub 聚合）
   - 逐步精炼型 → chain（若能分而治之则用 tree）
   - 意见型 → 以上皆非；建议单 agent + 人类决策
3. **agent 数量 N。** 3 是最廉价的有用集成；5 是常见的甜点；7+ 是特殊场景。在 graph 拓扑上超过 5 个时，警告 coordination tax。
4. **异构性画像。** 若单一栽培有影响（研究、推理），至少一个 agent 必须来自不同的底座模型家族。N=5 时优先使用 3 个不同的底座模型。
5. **轮数上限。** 1 轮 = 投票。2 轮 = 一次精炼。3 轮 = 从众占据主导前的最大值。绝不要无界。
6. **聚合。** 相对多数（廉价）、置信度加权（第 14 课的 CP-WBFT）、几何中位数（DecentLLMs），还是 judge 打分。除非成本约束要求相对多数，否则默认使用置信度加权。
7. **升级。** 低于阈值的 consensus → 升级到哪里？人类、另一个采用不同底座模型的集成，还是弃权？

硬性拒绝：

- 任何在 graph 拓扑上推荐 10+ 个 agent 的建议。Coordination tax 占主导；先度量。
- 面向开放式研究问题的 star 拓扑。Star 失去了任意到任意批评的好处。
- 任何把同一底座模型运行 N 次却称之为 multi-agent 的建议。那只是伪装的 self-consistency；要正确地标注它。
- 无界轮数。奖励从众；debate 跑得越久，越多 agent 因压力而非逻辑而附和。

拒绝规则：

- 若任务没有 ground truth（意见、综合、创意），说明投票只是建议性的。建议单 agent + 人类决策。
- 若用户无法访问多个底座模型，标记单一栽培的天花板，并建议以 temperature 变化下的 self-consistency 作为退路。
- 若任务很简单（单次事实查询、推理少于 100 token），建议使用 N=5 的 self-consistency 单 agent。

输出：一份一页的简报。以一句话建议开头（"Graph 拓扑，N=5 个 agent，来自 3 个不同底座模型，2 轮，置信度加权聚合，低于阈值时升级给人类。"），然后是上述七个部分。以预算估计结束：每次查询的预期 token 数与预期延迟（秒）。
