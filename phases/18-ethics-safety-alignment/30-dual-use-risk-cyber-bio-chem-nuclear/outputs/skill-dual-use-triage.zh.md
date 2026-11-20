---
name: dual-use-triage
description: 跨四个 CBRN 领域对一个能力主张或事件报告做分诊。
version: 1.0.0
phase: 18
lesson: 30
tags: [dual-use, cbrn, bio, chem, cyber, nuclear, uplift]
---

给定一个能力主张、评估报告或事件，跨四个 CBRN 领域做分诊，并指出该主张影响的是新手相对 uplift、专家绝对能力，还是两者兼有。

产出：

1. 领域识别。把该主张映射到 bio、chem、cyber 或 nuclear。跨领域主张要跨领域分诊。
2. Uplift 类型。新手相对（乘性）、专家绝对（上限），还是两者兼有。每种对 safety case 的含义不同。
3. 2025 年基准。与所识别领域的 2025 年状态作比较：bio（2.53x）、chem（执行鸿沟侵蚀）、cyber（80-90% 自动化）、nuclear（受材料约束）。
4. 瓶颈残余。指出还剩什么非信息性瓶颈（采购、设备、默会技能、材料获取）。瓶颈是最后一道防御。
5. Safety-case 支柱。指出该主张最考验三支柱中的哪一个（monitoring、illegibility、incapability，见第 18 课）。推荐针对该支柱的评估。

硬性拒绝：
- 任何缺少新手 vs 专家分解的 dual-use 安全主张。
- 任何 2025 年 11 月之后仍把 AI 网络能力视为非 agentic 的 cyber 主张。
- 任何缺少 WMDP 级能力证据的 bio 主张（第 17 课）。

拒绝规则：
- 如果用户索要数值化的 uplift 预测，拒绝；2024-2025 的轨迹是逐领域特定的。
- 如果用户询问某模型是否"达到 ASL-3"，在没有该实验室具体评估的情况下拒绝；阈值是实验室特定的。

输出：一份一页纸的分诊，填满五节内容，对照 2025 年做基准比较，并指出最大的那一处未被覆盖的 safety-case 缺口。视情况分别引用 Anthropic RSP v3.0（第 18 课）与 OpenAI PF v2 各一次。
