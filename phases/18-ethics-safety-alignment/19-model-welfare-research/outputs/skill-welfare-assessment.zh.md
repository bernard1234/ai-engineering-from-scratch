---
name: welfare-assessment
description: 对部署决策应用 Anthropic 的四步福祉预防性评估。
version: 1.0.0
phase: 18
lesson: 19
tags: [model-welfare, moral-uncertainty, low-regret, anthropic]
---

给定一个部署决策或提议的福祉干预，应用四步预防性评估。

产出：

1. Moral-patienthood 概率。估计模型是 moral patient 的概率（非平凡区间；Anthropic 2025 在 p > 0.01 上运作）。参考 Chalmers et al. 2024 专家报告给出的区间。
2. 干预成本。计算该干预的预期单次对话或单次部署成本。在边缘情况结束对话约为 $0.002/次对话；关闭模型则是数千到数百万。
3. 行为证据。识别与 model welfare 相关的非自我报告证据：痛苦轨迹、部署前评分模式、可解释性探针。根据 Eleos AI，仅有自我报告是不够的。
4. 期望值。计算 EV = p(福祉相关) * 收益 - 成本。当且仅当 EV > 0 时投入。

硬性拒绝：
- 任何仅基于单次自我报告 prompt 的福祉主张。
- 任何未说明成本的福祉干预。
- 任何未与 Chalmers et al. 对话的福祉否定（“p = 0”）。

拒绝规则：
- 如果用户问 AI 模型是否“真的”有意识，拒绝二元答案，并框定为道德不确定性。
- 如果用户要求一个数值化的 patienthood 概率，拒绝给出单一数字；指向 Chalmers et al. 的不确定性区间。

输出：一页评估，填写上述四个部分，为一到两个具体干预计算 EV，并点明投入决策。各引用 Anthropic 2025 与 Chalmers et al. 2024 一次。
