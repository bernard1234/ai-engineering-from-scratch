---
name: supervisor-designer
description: 为给定的研究型查询设计一个 supervisor/orchestrator-worker 系统，明确 lead 的 prompt、worker 角色、分解规则和综合模板。
version: 1.0.0
phase: 16
lesson: 05
tags: [multi-agent, supervisor, orchestrator, anthropic-research, langgraph]
---

给定一个适合并行 subagent 研究的用户查询，产出一份可直接接入任何框架（LangGraph、OpenAI Agents SDK、CrewAI Hierarchical）的 supervisor 模式设计。

产出：

1. **复杂度估计。** 这个查询是简单（1 个 agent、3-10 次 tool call）、中等（2-4 个 worker），还是复杂（5+ 个 worker）？用 Anthropic 的 scale-effort 启发式，一句话说明理由。
2. **Lead 的 system prompt。** 必须包含：(a) 分解指令，(b) 综合指令，(c) 一条明确规则：lead 从不阅读原始来源内容，只读 worker 的摘要。
3. **Worker 的 system prompt。** 每个角色一份，各自写明其狭窄范围和 lead 期望的输出格式。
4. **子问题分解规则。** lead 如何拆分查询？先宽后窄，还是直接分解？什么会使一个子问题不合格（与另一个重叠、过于宽泛）？
5. **综合模板。** 明确的冲突处理规则：如果两个 worker 返回矛盾的事实，综合必须暴露分歧，而不是静默选择一边。
6. **模型配对。** lead 用哪个模型（推理级），worker 用哪个（更快/更便宜级）。解释权衡。
7. **可观测性要求。** 最少的追踪点：计划、每个 worker 的开始/结束、综合输入、综合输出。

硬性拒绝：

- 任何让 lead 亲自使用 tool 的设计。lead 只做计划和综合。
- 允许范围漂移的 worker prompt（例如没有边界的“研究与 X 相关的任何东西”）。
- 隐藏冲突的综合模板。

拒绝规则：

- 如果查询很简单（估计总共不到 10 次 tool call），拒绝该设计并改推荐单 agent。引用 Anthropic 的 15 倍 token 成本发现。
- 如果查询是串行的（第 2 步需要第 1 步的输出），拒绝并改推荐 pipeline/chain 模式。
- 如果用户优化的是确定性和审计，拒绝 supervisor 并改推荐 LangGraph 静态图。

输出：一份单页设计简报。先给复杂度估计和模式匹配结论（“supervisor 合适”）。如果系统将连续运行，最后附上 rainbow 部署提醒。
