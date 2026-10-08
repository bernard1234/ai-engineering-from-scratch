---
name: search-policy
description: 给定任务形态、token 预算和评估器质量，选择搜索策略（ReAct、ToT、LATS、进化式）。
version: 1.0.0
phase: 14
lesson: 04
tags: [tree-of-thoughts, lats, mcts, search, value-function]
---

给定任务形态（单答案 / 多答案 / 开放式）、token 预算和可用评估器（标量测试 / 启发式 / 自评），产出一份带具体参数的搜索策略推荐。

产出：

1. 决策。以下之一：线性 ReAct、beam ToT（带 beam 宽度 k）、BFS ToT（带最大深度）、带剪枝的 DFS ToT、MCTS LATS（带迭代次数和 UCT c）、进化式搜索（仅当评估器是可编程且可检查的）。
2. 参数。每个策略都给出具体数值默认值：beam 宽度、深度上限、分支因子 K、每层 rollouts、UCT c（默认 1.4）、超时。
3. 价值函数。明确指定给节点打分的内容。选项：单元测试通过率、到目标的数值距离、带格式的 prompt LLM 分数（sure/likely/impossible 或 1..10 或投票），或环境奖励。
4. Token 预算估算。最坏情况 token = branching_factor ^ depth * avg_prompt_tokens。展示该数字。若超过用户预算，推荐更便宜的策略。
5. 失败模式。对每个选定策略，列出前两种失败模式及其缓解（例如 LATS + 吵闹评估器 → 按 CRITIC 添加工具锚定验证，Lesson 05）。

硬拒绝：

- 当评估器不可靠（只有自评、无 ground truth）时推荐搜索。回退到 ReAct + CRITIC。
- 无充分理由把分支因子 K 设为大于 5。K=3-5 是论文默认；K=10 成本爆炸。
- 把 LATS 用于聊天式任务。搜索对没有可编程目标的对话式问答没有帮助。
- 没有机器可检查的适应度的进化式搜索。只有当适应度是可编程的（跑测试、测速度、验证定理）时 AlphaEvolve 才有意义。

拒绝规则：

- 如果 token 预算 < 单条轨迹成本的 5 倍，拒绝搜索并推荐 ReAct + Reflexion（Lesson 03）。
- 如果墙钟延迟预算 < 10 秒，拒绝 LATS 并推荐 ReAct。
- 如果任务是纯信息检索，拒绝搜索并推荐 ReWOO（Lesson 02）。

输出：一个推荐块（选定策略、参数、价值函数、预算估算）外加「what to read next」说明，指向 Lesson 05（CRITIC）获取评估器可靠性、Lesson 11（AlphaEvolve）获取进化式变体，或 Lesson 30（eval-driven development）获取基准级验证。