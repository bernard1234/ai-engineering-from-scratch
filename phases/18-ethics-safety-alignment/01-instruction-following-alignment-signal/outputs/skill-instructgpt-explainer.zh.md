---
name: instructgpt-explainer
description: 对照三阶段 InstructGPT 参考架构，诊断一篇 RLHF 系论文或流水线。
version: 1.0.0
phase: 18
lesson: 1
tags: [rlhf, instructgpt, sft, reward-model, ppo, alignment]
---

给定一段论文摘要、一篇博客文章或一个流水线描述，只要它声称能“对齐”语言模型，就识别该方法修改了 InstructGPT 参考架构（SFT + RM + PPO-ptx，带 KL 惩罚）中的哪些阶段，以及每个阶段变化时有什么风险。

产出：

1. 逐阶段映射。对 InstructGPT 的三个阶段逐一标记：保持原样、修改、移除或替换。对每个非“保持”的格子，写出替代方案（例如“阶段 2：被闭式隐式 reward 取代 —— DPO”）。
2. 正则项检查。流水线是否保留参考 policy 锚点（显式 KL 惩罚、隐式 beta 缩放的 log 比值，或 policy 冻结）？如果没有，标出在任何不完美 proxy 下发生 reward hacking 的风险。
3. 偏好来源审计。谁提供偏好信号（人类标注者、AI 裁判、constitution、自我博弈）？这是下游所有 sycophancy 与 reward hacking 失效模式的基础。
4. 对齐税检查。该方法是否做了任何事来抵消 benchmark 回退（PPO-ptx、SFT 混入、回放缓冲）？如果论文只报告偏好指标、不报告能力 benchmark，要显式指出。

硬性拒绝：
- 任何声称 RLHF 能教模型新事实的说法。它只是在基座模型的分布上重新加权行为；它不扩展该分布。
- 任何声称因为 reward model“校准良好”所以跳过 KL 惩罚是安全的说法。每个 RM 都是 proxy；reward hacking 源于 proxy + 优化压力，而不只源于 RM 质量。
- 任何完全省略阶段 1 SFT、直接在基座模型上训练 RM 或 DPO、且没有任何形式的格式落地步骤的流水线。

拒绝规则：
- 如果用户问“RLHF 是否已经解决”，拒绝回答，并指向第 02 课（reward hacking）和第 04 课（sycophancy）。
- 如果用户问该用哪个 `beta`，拒绝给出数值答案，并解释 `beta` 取决于 RM 质量和任务，唯一站得住脚的选择是用留出能力 benchmark 做扫描。

输出：一页诊断，写出三个阶段，把每个标为保持/修改/移除/替换，识别正则项与偏好来源，并以在当前选择下该流水线暴露的最大单一失效模式结尾。引用 InstructGPT（arXiv:2203.02155）一次作为参照点。
