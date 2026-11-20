---
name: horizon-interpretation
description: 审查供应商的 time-horizon 声明，并产出 benchmark 声明与部署现实之间的差距分析。
version: 1.0.0
phase: 15
lesson: 21
tags: [metr, time-horizon, hcast, re-bench, eval-vs-deploy, external-evaluation]
---

给定供应商发布的 time-horizon 声明（例如“我们的模型能以 50% 可靠性完成 14 小时的任务”），产出一份差距分析，量化部署现实的落差，并标出任何方法上的弱点。

产出：

1. **方法审计。** 识别任务套件（HCAST、RE-Bench、SWAA 或专有套件）。确认 logistic 拟合已披露（斜率、样本量、置信区间）。没有披露方法的 horizon 只是营销声明。
2. **任务分布匹配。** 把供应商的 benchmark 任务分布映射到用户的生产任务分布。如果两者存在实质差异（供应商测的是 SWE 任务，生产是客户支持流程），这个数字就无法迁移。
3. **Eval 语境差距。** 在 benchmark horizon 与部署现实之间应用 10–40% 的差距。引用 Anthropic 2024 对齐伪装研究和 2026 International AI Safety Report 关于 eval-context gaming 的结论。实际差距取决于 eval 协议；在非结构化任务上 gaming 更高。
4. **工具差距。** Benchmark 工具干净且埋点完善。生产工具更混乱。估计再打 5–30% 的可靠性折扣。
5. **Human-in-the-loop 假设。** Benchmark 假设没有 HITL。带 HITL 的生产 agent 可靠性更高但自主性更低。据此调整 horizon 的解释。

硬性拒绝：
- 没有来源方法或样本量的 horizon 声明。
- 声称 benchmark horizon 能预测部署可靠性的说法。
- 供应商把 2025 或更早的 horizon 数字当作当前数字引用（倍增时间约 7 个月；2025 年的数字一年内就过时）。
- 把 50% horizon 当作“大部分时候都能用”——50% 可靠性就是抛硬币。

拒绝规则：
- 如果供应商不披露方法，拒绝，并要求提供来源论文或博客文章。
- 如果 benchmark 分布与生产分布没有重叠，拒绝，并要求做内部评估。
- 如果供应商引用 horizon 却没有针对其具体 eval 流水线做 gaming 审计，拒绝把该数字当作可靠性预测引用。

输出格式：

返回一份 horizon 解读备忘录，包含：
- **来源方法**（套件、拟合方法、样本量、CI）
- **分布重叠**（benchmark vs 生产；% 映射）
- **Eval 语境差距估计**（低 / 中 / 高，附理由）
- **工具差距估计**（低 / 中 / 高）
- **HITL 假设**（benchmark 式自主 vs 生产 HITL）
- **部署调整后的 horizon**（在差距与工具折扣之后的 horizon）
- **就绪结论**（生产 / 预发 / 仅研究）
