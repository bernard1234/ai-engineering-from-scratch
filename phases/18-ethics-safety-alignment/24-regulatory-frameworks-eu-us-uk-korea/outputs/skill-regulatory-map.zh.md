---
name: regulatory-map
description: 跨 EU、US、UK、Korea 映射部署的 AI 监管义务。
version: 1.0.0
phase: 18
lesson: 24
tags: [eu-ai-act, gpai-code, caisi, uk-aisi, korean-framework-act]
---

给定一段部署描述（提供者法域、基础设施法域、用户法域），映射适用的 AI 监管义务。

产出：

1. EU 暴露。如果部署触及 EU 用户或基础设施，则适用 EU AI Act。识别风险分级（禁止性、high-risk、GPAI-systemic、GPAI-other、limited）。说明每类义务的截止时间。
2. UK 暴露。如果是 UK 用户，说明 UK AI Security Institute 的评估预期。UK 在 2026 年没有综合性 AI 监管；适用部门化规则。
3. US 暴露。如果是 US 用户，识别联邦层面活动（CAISI、NIST 标准）与州级规则（加州 AB 2013、科罗拉多 AI Act 等）。联邦框架是促增长的；州级规则设定底线。
4. Korea 暴露。如果是韩国用户，则适用韩国 AI Framework Act；识别该部署属于高影响 AI 还是生成式 AI；对外国提供者标出本地代表要求。
5. 约束规则判定。对每项实质义务（透明度、风险评估、版权），找出跨法域中最严格的规则。那就是约束规则。

硬性拒绝：
- 任何未点明适用法域的部署映射。
- 任何未识别风险分级的 EU 暴露评估。
- 任何忽略州级规则的 US 暴露评估。

拒绝规则：
- 如果用户问“这个部署是否合规”，在没有逐法域映射的情况下拒绝二元主张。
- 如果用户要求单一的全球合规策略，拒绝——各法域的要求不同。

输出：一页映射，填写上述五个部分，在每个实质问题上点明约束规则，并点明风险最高的合规缺口。各引用 EU AI Act（Regulation 2024/1689）、GPAI Code of Practice（2025）与韩国 AI Framework Act 一次。
