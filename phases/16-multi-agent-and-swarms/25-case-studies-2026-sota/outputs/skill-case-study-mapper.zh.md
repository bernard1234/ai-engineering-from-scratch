---
name: case-study-mapper
description: 把一个拟议的多 agent 系统设计映射到最接近的 2026 年生产参考（Anthropic Research、MetaGPT/ChatDev，或 OpenClaw/Moltbook）。指出已知权衡、推荐框架，以及已在生产中验证过的具体设计决策。
version: 1.0.0
phase: 16
lesson: 25
tags: [multi-agent, case-studies, production, framework-selection, reference-architectures]
---

给定一个拟议的多 agent 系统设计，挑出最接近的 2026 年正典案例研究并做适配。

产出：

1. **设计指纹。** 任务类型（研究 / 工程 / 群体 / 自动化）、agent 数量、验证要求、运行时长、角色区分度、面向用户的网络暴露。
2. **最接近的案例研究。**
   - 若属以下情形则选 **Anthropic Research**：研究或知识检索任务、验证为必需、多小时运行、agent 差异主要体现在上下文与范围（fresh-context 子 agent 占优）。
   - 若属以下情形则选 **MetaGPT / ChatDev**：工程或结构化工作流、角色清晰可辨（规划者 / 编码者 / 评审者 / 测试者）、交接产物类型明确。
   - 若属以下情形则选 **OpenClaw / Moltbook**：群体规模、面向用户的 agent 网络、prompt injection 是实质威胁、涌现经济重要。
3. **可复制的模式。** 所选案例研究中适用的具体设计决策：fresh-context 子 agent、rainbow 部署、communicative dehallucination、DAG 路由、不可写验证器、基底级安全。
4. **框架推荐。** LangGraph、CrewAI、AG2、Microsoft Agent Framework、OpenAI Agents SDK、Google ADK、Anthropic Claude Agent SDK，或自研。默认用案例研究的典型框架；若针对该设计有更合适的选项，注明。
5. **来自案例的反模式。** 参考案例发现行不通的做法。在新设计中避免。
6. **成本预估。** 预期 token 倍数（Anthropic Research：约 15x；MetaGPT：约 5x；OpenClaw：取决于网络效应）。预期墙钟时间与美元成本区间。
7. **评估方式。** 相关 benchmark（MARBLE、SWE-bench Pro、内部）；相对案例基线，设定多大差值算合理目标。

硬性否决：

- 任务有正确性要求却忽略验证的设计。每个案例研究都付了验证税。
- 声称新基底却不把 prompt injection 视为攻击面的设计。OpenClaw/Moltbook 案例表明这是生产关切，而非假想。
- 无法映射到任何案例研究的"革命性"声称。多 agent 自 2024 年起就已在生产中使用；新颖声称需要明确的对比。
- 无正当理由就跳过 MCP 或 A2A 采用的设计。协议支持是基本门槛。

拒绝规则：

- 若设计没有明确任务类型，建议先界定任务范围再选案例研究。"万物皆多 agent"不是设计。
- 若设计声称生产就绪却没有失效模式审计，建议先做 MAST 风格审计（第 23 课）再做参考映射。
- 若设计纯属实验 / 研究，注明在采用任何案例研究的生产模式前，哪些方面需要加固。

输出：一份两页的简讯。先用一句话总结（"最接近的案例研究：MetaGPT / ChatDev。采用 role-SOP 分解、communicative dehallucination 与结构化交接产物；使用 CrewAI 或自研。"），然后是上面七个部分。最后给出 90 天适配计划：从参考中复制什么、自定义什么、对照 benchmark 验证什么。
