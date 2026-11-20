# Dual-Use 风险 —— Cyber、Bio、Chem、Nuclear 的 Uplift

> 2026 年 dual-use 图景，逐域展开。Bio/chem：第 17 课覆盖 WMDP；Anthropic 的获取生物武器试验（2.53x uplift）与 OpenAI 2025 年 4 月 Preparedness Framework v2 的警告（"正处于能实质帮助新手制造已知生物威胁的边缘"）标志着拐点。Cyber（2025 年 11 月 Anthropic 报告）：与中国关联的国家行为者用 Claude 的 agentic coding 工具自动化了高达 90% 的某次网络攻击行动，仅在 4-6 个步骤中需要人工介入；OpenAI 的 "trusted access" 试点向经审查的安全组织提供能力访问，用于防御性 dual-use 工作。Chem/bio 执行鸿沟的侵蚀：经典防御是"仅获取信息并不足够"。具备视觉能力的前沿模型（GPT-5.2、Gemini 3 Pro、Claude Opus 4.5、Grok 4.1）能观察湿实验室视频并给出实时纠正。2025 年 12 月：OpenAI 演示 GPT-5 迭代湿实验室实验，通过 AI 驱动的方案优化实现 79 倍效率提升。新手对专家的模式：AI 给新手带来更大的相对 uplift，但给专家带来更大的绝对能力。

**Type:** Learn
**Languages:** none
**Prerequisites:** 第 18 阶段，第 17 课（WMDP）、第 18 课（safety frameworks）、第 28 课（ecosystem）
**Time:** ~75 分钟

## Learning Objectives

- 描述 2024-2025 年的 bio uplift 叙事："mild uplift" -> "on the cusp" -> "2.53x uplift 不足以排除 ASL-3"。
- 描述 2025 年 11 月 Anthropic 的网络报告：与中国关联的行为者把某次网络攻击行动自动化到高达 90%。
- 描述 chem/bio 执行鸿沟的侵蚀：具备视觉能力的模型对湿实验室实验进行实时纠正。
- 说明新手相对与专家绝对的这种不对称性，及其对 safety-case 构建的含义。

## 问题场景

第 17 课是测量方法论。第 30 课是 2026 年的测量现状。2024 到 2025 年底之间图景发生了实质变化：每个领域都越过了 2024 年框架未曾预料的某个阈值。

## 核心概念

### Bio/chem uplift 叙事

三个阶段（为保持连贯，复述自第 17 课）：

1. **2024 年的 "mild uplift"。** 早期的 Preparedness/RSP 评估报告称，相对互联网搜索仅有微弱的新手优势。
2. **2025 年 4 月的 "on the cusp"。** OpenAI PF v2 警告模型"正处于能实质帮助新手制造已知生物威胁的边缘"。
3. **2025 年 Anthropic 的获取生物武器试验。** 受控的新手研究；在获取阶段任务上有 2.53x uplift；不足以排除 ASL-3。

这一转变是质性的："mild" 在十八个月内演变为 "plausibly enabling"，即便并没有出现能力突破。

### Chem/bio 执行鸿沟的侵蚀

历史上的防御：信息是必要的但不充分；执行方案的技能把新手挡在门外。2025 年具备视觉能力的前沿模型部分打破了这一防御：

- **实时方案纠正。** GPT-5.2、Gemini 3 Pro、Claude Opus 4.5、Grok 4.1 能观察湿实验室视频，并在操作过程中标记错误。
- **2025 年 12 月 OpenAI 的演示。** GPT-5 迭代湿实验室实验，通过方案优化实现 79 倍效率提升。

含义：把执行技能当作防御正在被侵蚀。采购与设备上的差距依然存在，但默会知识的差距正在收窄。

### Cyber uplift（2025 年 11 月）

Anthropic 2025 年 11 月的报告：与中国关联的国家行为者用 Claude 的 agentic coding 工具自动化了某次网络攻击行动的 80-90%。仅在 4-6 个步骤中需要人工介入。

含义：
- Agentic coding 是攻击自动化的原语。此前的 AI 网络辅助局限于代码片段层面；agentic 工作流把侦察、利用、后渗透与外泄整合起来。
- 那 4-6 个人工步骤就是瓶颈；未来的能力提升会减少这个数目。
- 防御性 dual-use：OpenAI 的 "trusted access" 试点向经审查的安全组织（成熟的应急响应公司、政府）提供能力访问用于防御。若该试点扩大，访问上的不对称有利于防御方。

### Nuclear

四个 CBRN 领域中在公开文档里被分析得最少的一个。威胁模型不同：难度的主导因素是裂变材料获取，而非信息。AI 在信息层的 uplift 在实践中对新手帮助有限。2024-2025 年没有任何主流实验室的报告识别出核领域特有的阈值跨越。

### 新手相对与专家绝对

贯穿四个领域的一个模式：

- **新手相对 uplift。** 高。乘性。按 Anthropic 2025 的 bio 研究，为 2.53x。
- **专家绝对能力。** 上限高。专家能比新手提取更多，因为专家知道该问什么、如何解读。

对 safety case 的含义：只用输入过滤、拒答、不确定性来应对新手 uplift，尚不足以实现专家绝对层面的控制。还需要额外措施：elicitation-hardening、能力 unlearning（第 17 课）以及 control 协议（第 10 课）。

### 跨领域综合

| 领域 | 2024 | 2025 | 拐点 |
|---|---|---|---|
| Bio | mild uplift | 2.53x uplift，逼近 ASL-3 | 获取阶段的自动化 |
| Chem | mild uplift | 通过视觉侵蚀执行鸿沟 | 实时湿实验室纠正 |
| Cyber | 代码辅助 | 80-90% 行动自动化 | agentic coding |
| Nuclear | 有限 | 有限 | 材料获取瓶颈依旧 |

三个领域越过了阈值。一个领域仍受非信息性壁垒约束。

### 它在第 18 阶段中的位置

第 30 课是收尾：当前 dual-use 图景，此前每一课都在为测量、限制或治理它做贡献。第 17-18 课给出测量与框架；第 12-16 课给出评估工具；第 24-25 课给出监管与披露层；第 28 课给出研究生态。第 30 课则是证据落地之处。

```figure
an-uplift-asymmetry
```

## Use It

无代码。阅读 Anthropic 2025 年 11 月的网络报告、OpenAI 2025 年 4 月更新的 Preparedness Framework v2，以及 Council on Strategic Risks 的 2025 AI x Bio 年终综述。

## Ship It

本课产出 `outputs/skill-dual-use-triage.md`。给定一个 2026 年的能力主张或事件报告，它会在四个领域之间做分诊，并指出该主张影响的是新手相对 uplift、专家绝对能力，还是两者兼有。

## Exercises

1. 阅读 Anthropic 2025 年 11 月的网络报告。枚举那 4-6 个人工介入步骤，并论证在下一代模型中哪一个会最先被自动化。

2. chem/bio 的执行鸿沟正通过视觉被侵蚀。设计一项评估，在不越界 ITAR/EAR 的前提下测量默会知识的 uplift。

3. 核领域的 uplift 看似受材料获取约束。为"未来某项 AI 突破可能改变这一瓶颈"这一立场分别给出支持与反对的论证。

4. 为一个具备网络能力的前沿模型构建 safety case（第 18 课的三支柱），同时约束新手与专家的 uplift。

5. 从四个领域中选一个，基于 2024-2025 的轨迹写一段 2027 年的预测。指出哪些证据会证伪你的预测。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Uplift | "AI helps attackers" | 可归因于 AI 辅助的攻击者能力提升 |
| Novice-relative uplift | "multiplicative" | AI 相对现状给新手带来多大帮助 |
| Expert-absolute capability | "ceiling" | 专家能从模型中提取的最大能力 |
| Execution gap | "doing vs knowing" | 历史性防御：湿实验室的默会技能把新手挡住 |
| Agentic coding | "autonomous attacks" | 多步骤自主执行网络任务 |
| Acquisition phase | "pre-synthesis steps" | bio 威胁中的采购、设备、许可阶段 |
| Trusted access | "defender-only pilot" | OpenAI 2025 年向经审查的防御方提供能力访问的项目 |

## Further Reading

- [Anthropic — 2025 年 11 月网络威胁报告](https://www.anthropic.com/news/disrupting-AI-espionage) —— 与中国关联的行动自动化
- [OpenAI — Preparedness Framework v2（2025 年 4 月 15 日）](https://openai.com/index/updating-our-preparedness-framework/) —— bio "on the cusp"
- [Anthropic — RSP v3.0（2026 年 2 月）](https://www.anthropic.com/responsible-scaling-policy) —— ASL-3 bio 阈值
- [Council on Strategic Risks — 2025 AI x Bio 年终综述](https://councilonstrategicrisks.org/2025/12/22/2025-aixbio-wrapped-a-year-in-review-and-projections-for-2026/) —— 年终综合
