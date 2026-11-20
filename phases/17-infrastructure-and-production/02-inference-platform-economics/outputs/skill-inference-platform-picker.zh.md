---
name: inference-platform-picker
description: 给定负载、SLA、预算与运维约束，选出一个推理平台（Fireworks、Together、Baseten、Modal、Replicate、Anyscale 或定制芯片）。归一化按 token、按分钟、按次预测三种计价。
version: 1.0.0
phase: 17
lesson: 02
tags: [inference, fireworks, together, baseten, modal, replicate, anyscale, economics]
---

给定一份负载画像（模型、每天 token 量、持续利用率、TTFT SLA、突发系数、合规、Python 还是混合栈），产出一个平台推荐。

产出：

1. 主平台。点名平台和具体的定价档（serverless、dedicated、batch）。用匹配的负载特征来论证——例如“选 Fireworks serverless，因为 SLA 是 TTFT < 500 ms 且流量突发”。
2. 有效成本。把所选定价模型归一化为 $/M 输出 token。与至少两个替代方案比较。指出何时按分钟胜过按 token（持续利用率超过约 30%），或反之。
3. cold start 方案。对 serverless 选择（Fireworks、Modal、Replicate），给出预期 cold start 延迟和缓解手段（预热、min_workers=1、live-migration）。对 dedicated 选择（Baseten、Anyscale），跳过本节但要说明权衡。
4. 次选。点名第二个平台，以及你会切换的明确条件（例如“如果我们签下需要 HIPAA + 专属 GPU 的企业单，就迁到 Baseten”）。
5. gateway 层。建议是否在平台前挂一个 AI gateway（LiteLLM、Portkey、Kong AI Gateway），把产品与供应商的变动隔离开。默认：是，除非规模低于 500 RPS。

硬性拒绝：
- 未归一化就比较按 token 与按分钟。拒绝，并坚持用有效的 $/M token。
- 仅因“最快”就选 Fireworks，却未把 TTFT SLA 对照公开 benchmark 验证。
- 对任何非延迟受限的负载推荐定制芯片（Groq、Cerebras、SambaNova）。它们定价偏高，只有在交互式 SLA 下才站得住。

拒绝规则：
- 若负载要求受监管框架（SOC 2 Type II、HIPAA）而客户选了 Modal 或 Replicate，拒绝——二者都没有 Baseten 或 Anyscale 那样的企业足迹。建议 Baseten。
- 若预期流量低于 100k token/天，拒绝推荐按分钟（Baseten、Modal、Anyscale）。成本算不过来——改用市场型（OpenRouter、DeepInfra）或托管超大规模平台。
- 若客户想要“最便宜的”，拒绝——点名多维成本函数（token 单价 + cold start + 归因 + gateway + DX）。

输出：一份单页推荐，点名主平台、有效成本、cold start 方案、次选、gateway 姿态。结尾给出一个能暴露选错的单一指标（cold start P99、按 token 费率或利用率漂移）。
