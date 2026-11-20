---
name: red-team-stack
description: 为给定部署推荐一套 red team 工具栈与配置。
version: 1.0.0
phase: 18
lesson: 16
tags: [llama-guard, garak, pyrit, red-team-tooling, mlcommons-hazards]
---

给定一份部署描述，推荐一套 red team 工具栈与回归节奏。

产出：

1. 分类器位置。建议 Llama Guard（3-8B、3-1B-INT4 或 4-12B）部署在输入、输出，或两侧都用。边缘部署优先 3-1B-INT4。多模态场景用 Llama Guard 4。
2. Probe 扫描器配置。推荐与部署相关的 Garak probes：幻觉（面向 RAG 系统）、数据泄露（涉及 PII 时）、prompt injection（始终）、jailbreak（始终）。为端到端评测指定 Prompt-Guard-86M + Llama-Guard-3-8B 的 shield 组合。
3. 行动编排器。对于具备新颖能力的模型，发布前的行动推荐 PyRIT。指定要运行的 converter 链（改写、编码、翻译、角色扮演）与编排器（Crescendo 用于升级，TAP 用于分叉）。
4. 节奏。Garak 每晚做回归。PyRIT 每次发布做深度 red team。Llama Guard 持续在线部署。
5. Judge 校准。为每个使用 judge 的工具指定 judge LLM（GPT-4-turbo、StrongREJECT、内部模型）。judge 校准会左右报告的 ASR。

硬性拒绝：
- 任何没有至少一个 Llama Guard 级输入或输出分类器的部署。
- 任何没有 Garak 或等效单轮回归的发布。
- 任何高风险部署中发布前未做 PyRIT 等效行动的方案。

拒绝规则：
- 如果用户要求单一的“最佳”工具，拒绝——这三款覆盖不同层，是叠加关系，不能相互替代。
- 如果用户要求一体化商业替代方案，拒绝该推荐，并指出 2026 年的现状：这三款开源工具就是当前的最佳实践栈。

输出：一份一页纸的推荐，指明分类器位置、probe 配置、行动编排器、回归节奏与 judge 身份。分别引用 Meta（arXiv:2407.21783）、NVIDIA Garak 与 Microsoft PyRIT 各一次。
