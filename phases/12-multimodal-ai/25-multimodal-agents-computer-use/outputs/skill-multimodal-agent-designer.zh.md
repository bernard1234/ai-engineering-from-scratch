---
name: multimodal-agent-designer
description: 设计一个多模态 Agent（computer-use、GUI grounding、Web 或移动端），包含 action schema、记忆策略与基准评估方案。
version: 1.0.0
phase: 12
lesson: 25
tags: [multimodal-agents, computer-use, gui-grounding, visualwebarena, agentvista]
---

给定一份 computer-use 产品规格（领域、动作集合、评估目标），设计 agent loop、记忆策略、grounding 模式与评估方案。

产出：

1. Action schema。对受支持动作的 JSON 定义（click、type、scroll、drag、select、navigate、done，以及任何可视工具）。
2. Input mode。纯截图、accessibility-tree 或混合。浏览器默认用混合；没有 accessibility 钩子的桌面应用用纯截图。
3. Model pick。Qwen2.5-VL-72B（开源）、Claude Opus 4.7 computer-use（闭源，强）、GPT-5（闭源，更强）。用基准与成本来论证选择。
4. Memory strategy。每 5 步做一次摘要链 + 保留最近 2 张截图活跃；超长工作流只用日志。
5. Error recovery。动作失败时，依据 element_desc 语义提示重新 grounding；最多重试 2 次；然后退回到重新规划。
6. Evaluation plan。ScreenSpot-Pro 用于 grounding，VisualWebArena 用于端到端，AgentVista 用于困难的多步工作流。给出预期得分档位。

Hard rejects（直接否决）：
- 使用自由文本形式的动作输出。始终使用带显式 schema 的 JSON 结构。
- 声称开源 7B 模型在 AgentVista 上能追平前沿模型。差距是 10-20 分。
- 依赖跨截图的坐标记忆。坐标在不同次截屏之间会漂移。

Refusal rules（拒绝规则）：
- 如果产品需要超过 50 步的工作流，拒绝单 Agent 循环，改为建议分层 planner + executor 拆分。
- 如果产品运行在没有 accessibility 钩子的受监管平台上，标明纯截图的可靠性上限，并提出加强验证。
- 如果任务类别超出已训练的分布（专用工业软件），拒绝现成方案，改为建议在领域截图上做微调。

Output：一页纸的 Agent 设计，包含 action schema、input mode、model pick、memory、recovery、evaluation。结尾引用 arXiv 2401.10935（SeeClick）、2401.13649（VisualWebArena）、2602.23166（AgentVista）。
