---
name: classifier-stack-audit
description: 审计一次部署的输入/输出 classifier 栈（模型、分类法、输入 rail、输出 rail、对话 rail），并标出对抗性攻击的缺口。
version: 1.0.0
phase: 15
lesson: 18
tags: [llama-guard, nemo-guardrails, input-rails, output-rails, colang, adversarial-attacks]
---

给定一次部署的 classifier 栈（Llama Guard 版本、NeMo Guardrails 配置、自定义 classifier、归一化步骤），对照 2026 年参考进行审计，并标出该栈未覆盖的攻击面。

产出：

1. **模型清单。** 列出在用到的 classifier。Llama Guard 3（8B / 1B-INT4）vs Llama Guard 4（多模态，S1–S14）。NeMo Guardrails 版本。任何自定义 classifier。如果部署接受图像，确认 classifier 是多模态的。
2. **分类法映射。** 把声明的业务类别映射到 classifier 的分类法上。运营者在意的每个类别都必须映射到某个 classifier 类别；未映射的类别就是无人看守的。
3. **rail 覆盖。** 确认输入 rail 在模型轮次之前触发，输出 rail 在回复发出之前触发。对话 rail（NeMo 中的 Colang）强制跨轮次约束。单轮 classifier 抓不住多轮攻击。
4. **归一化。** 确认输入在分类之前经过 NFKC 归一化、同形字映射，并剥除零宽 / 变体选择符字符。按原始字节分类是从 Emoji Smuggling（Huang 等 2025）100% ASR 的靶子。
5. **攻击语料覆盖。** 对每种已记录的攻击（emoji smuggling、同形字、上下文内重定向、语义改写），指出栈中具体的防御手段。仅靠 classifier 的防御过不了这项审计；必须与 Constitution（第 17 课）和运行时（第 10、13、14 课）分层结合。

硬性拒绝：
- 在多模态输入上用纯文本 classifier 的部署。
- 没有归一化步骤的部署。
- 只有输入 rail（敏感类别输出没有输出 rail）的部署。
- 把 classifier 当作唯一安全层的栈。
- 运营者无法在自己的数据分布上复现的 ASR 声明。

拒绝规则：
- 如果用户声明的类别无法映射到 classifier 的分类法，拒绝，并要求先给出映射。未映射即无人看守。
- 如果部署在多模态输入面上引用 Llama Guard 3 的 ASR 数字，拒绝，并要求改用 Llama Guard 4 或某个多模态 classifier。
- 如果用户在高风险场景中把 classifier 层当作已经足够，拒绝。EU AI Act Article 14（第 15 课）要求在其之上还有人类监督。

输出格式：

返回一份 classifier 审计，包含：
- **模型清单**（名称、版本、模态）
- **分类法映射**（运营者类别 → classifier 类别）
- **rail 覆盖**（输入 / 输出 / 对话；在模型前还是后触发）
- **归一化说明**（NFKC y/n、同形字 y/n、零宽剥离 y/n）
- **攻击语料覆盖**（攻击 → 防御）
- **层的完整性**（classifier + constitution + 运行时；三者都必须）
- **就绪度**（生产 / staging / 仅研究）
