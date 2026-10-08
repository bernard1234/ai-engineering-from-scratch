---
name: reflexion-buffer
description: 为 verbal RL 维护一个反思的情节记忆缓冲区，带 TTL、去重和 scope 隔离。
version: 1.0.0
phase: 14
lesson: 03
tags: [reflexion, episodic-memory, self-healing, verbal-rl, sleep-time]
---

给定一个任务类别（重复发生的 agent 运行类型——例如「重构一个函数」「关闭一个支持工单」），维护一个反思的情节记忆缓冲区。每条反思用自然语言记录一个失败模式和纠正性洞见。缓冲区被前置到同一任务类别的下一次试验。

产出：

1. 反思捕获。在一次试验以低于阈值的评估器分数结束后，以「I failed to do X because Y; next time, Z.」的形态产出一条单行反思。丢弃关于外部故障（网络、上游 500）的反思，除非它们可复现。
2. TTL 与去重。反思默认在 N 次试验后过期（建议 10）。完全重复合并。近似重复（小型 embedding 模型上余弦 >0.9，或公共子串 >= 80%）只保留最新一条。
3. Scope 策略。三种 scope：task-class（按任务名）、user（同一用户的跨任务）、agent（跨所有用户）。默认是 task-class。只有当反思涉及用户特定的偏好时才升级到 user scope；绝不自动升级到 agent scope。
4. 压缩。当缓冲区超出预算时，运行 sleep-time 压缩：聚类近似重复、摘要、合并。压缩在热路径之外运行——不要拖延主 agent 的响应。
5. Prompt 集成。产出一个标题为「What I learned from prior trials」的单一块和一个项目符号列表。在 prompt 里最多 6 条；溢出进入一个单独的摘要条目（「……以及 4 条更早的关于超时的反思」）。

硬拒绝：

- 把反思写成「下次更小心」。这不可执行。用一个强制产出具体「下次」指令的 prompt 重新运行反思器。
- 基于墙钟时间而非试验次数让反思过期。对于可离线重放的运行，TTL 应按试验次数而非时间界定。
- 存储引用机密（API key、token、PII）的反思。在提交进缓冲区之前，以特定的「contains secret」类错误拒绝。

拒绝规则：

- 如果没有挂接评估器，拒绝并推荐 Lesson 05（Self-Refine/CRITIC）——反思需要信号，而不是直觉。
- 如果任务类别是一次性的（永不复发），拒绝；情节记忆对一个永不重复的任务毫无作用。

输出：一个结构化缓冲区文件（JSON，反思对象含：trial id、task class、scope、text、created_at、ttl_remaining）、一个用于下一次试验的 prompt 块，以及一份「stale reflections」报告，列出即将过期的条目。

结尾加「what to read next」说明：如果缓冲区一再触顶，指向 Lesson 06（上下文压缩）；或指向 Lesson 08（Letta sleep-time compute）以把压缩移出热路径。