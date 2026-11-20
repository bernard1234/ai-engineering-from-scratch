---
name: groupchat-selector
description: 为任务配置一个 AutoGen/AG2 风格的 GroupChat 选择器，命名选择器变体、终止方式，以及防热门发言者的规则。
version: 1.0.0
phase: 16
lesson: 10
tags: [multi-agent, groupchat, autogen, ag2, speaker-selection]
---

给定一个任务和一份 agent 名册，产出一份 GroupChat 配置：选择器选择、选择器输入、终止规则，以及防线。

产出：

1. **选择器变体。** 轮转（便宜、公平、不感知上下文）、LLM 选择（感知上下文、昂贵），或自定义（LLM + 基于规则的兜底）。
2. **选择器输入。** 若用 LLM 选择：最近的 N 条消息、agent 专长、轮次计数。若用自定义：显式规则。
3. **终止规则。** 最大轮数、TERMINATE token、目标达成校验器，或组合使用。
4. **热门发言者缓解。** 每个 agent 的轮次上限、选择器输入中的发言均衡得分、连续 K 轮后强制轮换。
5. **上下文膨胀缓解。** 投影方案（每个角色限定视野）、摘要检查点、每个 agent 的上下文上限。
6. **可观测性。** 记录选择器的输入、选择器的选择、每轮 agent 延迟。

硬性拒绝：

- 任何 LLM 选择的配置，若不记录选择器的输入/输出，调试将变得不可能。
- 没有 max_rounds 上限的配置。
- 在推理任务上采用对称会话（无专业化）——改为使用辩论（第 07 课）。

拒绝规则：

- 如果任务有已知的 DAG 结构，拒绝 GroupChat，改为推荐 LangGraph 静态图以获得确定性。
- 如果任务要求严格的审计轨迹，拒绝 GroupChat；推荐带 checkpointer 的 LangGraph。
- 如果 agent 数量超过 5-6 个，拒绝扁平 GroupChat，推荐嵌套分组或分层模式。

输出：一页纸 GroupChat 配置简报。结尾给出成本估算（LLM 选择每轮产生一次选择器调用）。
