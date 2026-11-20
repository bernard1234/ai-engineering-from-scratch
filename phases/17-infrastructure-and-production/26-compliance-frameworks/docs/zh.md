# Compliance —— SOC 2、HIPAA、GDPR、PCI-DSS、EU AI Act、ISO 42001

> 多框架覆盖是 2026 年企业级交易的入场券。**EU AI Act**：自 2024 年 8 月 1 日起生效。大多数高风险要求在 2026 年 8 月 2 日执法。高风险系统义务的罚款最高 €15M 或全球年营业额的 3%（Art. 99(4)）；被禁止的 AI 实践最高 €35M 或 7%（Art. 99(3)）。只要服务欧盟用户，就在全球范围内适用。**Colorado AI Act**：2026 年 6 月 30 日生效（由 SB25B-004 从 2026 年 2 月推迟）—— 对高风险系统做影响评估、对 AI 决策有申诉权。Virginia 在信贷/就业/住房/教育方面有类似规定。**SOC 2 Type II**：事实上的 B2B AI 要求（对金融科技要 Type II，而非 Type I）。**GDPR**：有记录以来最大的 AI 专项罚款是 €30.5M，针对 Clearview AI（荷兰 DPA，2024 年 9 月）；意大利 Garante 于 2024 年 12 月对 OpenAI 开出 €15M（后于 2026 年 3 月上诉被推翻）。推理时实时 PII 脱敏才是站得住脚的标准；后处理清洗不够。**HIPAA**：受医疗约束 —— 没有 BAA 就不能把 PHI 发给外部 AI 服务。**PCI-DSS**：AI 交互层的覆盖需要配置 + 合同协议，不会自动获得。**ISO 42001**：新兴的 AI 治理标准，正与 ISO 27001 一起成为越来越多的采购要求。参考画像：OpenAI 持有 SOC 2 Type 2、ISO/IEC 27001:2022、ISO/IEC 27701:2019、GDPR/CCPA/HIPAA（BAA）/FERPA，以及针对 ChatGPT 支付组件的 PCI-DSS。跨框架映射能减少审计疲劳：访问控制可映射到 ISO 27001 A.5.15-5.18、GDPR Art. 32、HIPAA §164.312(a)。

**Type:** Learn
**Languages:** Python 可选 —— compliance 是策略 + 流程，而非代码
**Prerequisites:** 第 17 阶段，第 25 课（Security），第 13 课（Observability）
**Time:** ~60 分钟

## Learning Objectives

- 列举 2026 年与 LLM 产品相关的七个框架，并各匹配一个客户细分。
- 援引 EU AI Act 的执法时间线（2024 年 8 月生效；2026 年 8 月高风险执法）以及双档罚款上限（高风险义务 €15M / 3%，被禁止的实践 €35M / 7%）。
- 解释为什么后处理 PII 清洗对 GDPR 不够，并指出推理层实时脱敏才是站得住脚的标准。
- 描述跨框架控制映射（例如访问控制映射到 ISO 27001 A.5.15-5.18 + GDPR Art. 32 + HIPAA §164.312(a)）。

## 问题场景

一个企业客户的采购团队要求 SOC 2 Type II、GDPR、HIPAA BAA、ISO 27001，以及一份“EU AI Act 合规声明”。你的团队只有 SOC 2 Type I。距离 Type II 还有六个月，GDPR Article 30 记录还没开始做。

多框架覆盖不是 LLM 问题 —— 它是企业级 SaaS 问题，只是叠加了 LLM 专属的部分。2026 年的采购团队想要一张矩阵，每个框架一行、每个控制项一列，而不是一个 PDF。

## 核心概念

### 七个框架

| 框架 | 范围 | LLM 专属要求 |
|-----------|-------|--------------------------|
| SOC 2 Type II | B2B SaaS 基线 | 在 6-12 个月内接受审计的流程控制 |
| HIPAA | 美国医疗 | 必须有 BAA；没有签署协议，PHI 不能离开基础设施 |
| GDPR | 欧盟用户 | 实时 PII 脱敏；数据主体权利；Article 30 记录 |
| PCI-DSS | 支付数据 | 触及支付的 AI 需要配置 + 合同 |
| EU AI Act | 服务欧盟用户 | 风险分级；高风险系统：合格性评估、文档、日志 |
| Colorado AI Act | 服务科罗拉多州居民 | 影响评估；申诉权 |
| ISO 42001 | AI 治理 | 新兴；与 ISO 27001 配套 |

### EU AI Act 时间线

- 2024 年 8 月 1 日：生效。
- 2025 年 2 月 2 日：被禁止的 AI 实践开始执法。
- 2026 年 8 月 2 日：高风险系统开始执法（合格性评估、文档、日志）。
- 2027 年 8 月：受协调立法约束的产品中的高风险系统。

风险分级：不可接受（禁用）、高风险（合格性 + 日志）、有限风险（透明度）、最低风险（无约束）。大多数 B2B LLM SaaS 属于有限风险；高风险适用于就业、信贷、教育、执法、移民、基本服务。

罚款（Article 99）：违反高风险系统义务最高 €15M 或全球年营业额的 3%（Art. 99(4)）；被禁止的 AI 实践最高 €35M 或 7%（Art. 99(3)）；取较高者。

### GDPR —— 实时脱敏才是标准

后处理清洗（在 LLM 看到之后再脱敏 PII）不是站得住脚的姿态 —— 模型已经看到数据了。推理层实时脱敏才是 2026 年的标准：

- 在 LLM 调用前做实体识别。
- 一致性 tokenization（Mesh 方法）保留语义。
- 只存脱敏后的 prompt，原始 prompt 仅在用户同意下保留。

近期执法：€30.5M 针对 Clearview AI（荷兰 DPA，2024 年 9 月）是迄今有记录的最大 AI 专项 GDPR 罚款；€15M 针对 OpenAI（意大利 Garante，2024 年 12 月）是最大的 LLM 专项罚款，尽管它于 2026 年 3 月在上诉中被推翻，裁决仍在进一步审查中。后处理的主张在审计中已经站不住。

### HIPAA —— BAA 不可省略

没有签署 Business Associate Agreement，你就不能把 PHI 发给外部 AI 服务。三家超大规模 LLM 平台（Bedrock、Azure OpenAI、Vertex）都提供 BAA。OpenAI 直连 API 提供 BAA。Anthropic 直连 API 提供 BAA。发送 PHI 前先确认。

### SOC 2 Type II

Type I：控制已设计并记录在案。
Type II：控制在 6-12 个月内有效运行。

2026 年的 B2B 采购默认要求 Type II。Type I 是入门；Type II 才是门槛。

常见审计驱动项：访问日志（谁看了什么）、变更管理（如何部署的）、风险评估（每季度）、事件响应（测试过吗？）。Phase 17 · 25 的审计日志可直接复用。

### 跨框架映射

一条访问控制策略可以满足多个框架的控制项：

| 控制项 | 框架 |
|---------|-----------|
| 访问日志 | ISO 27001 A.5.15-5.18、GDPR Art. 32、HIPAA §164.312(a) |
| 变更管理 | ISO 27001 A.8.32、PCI DSS Req. 6、HIPAA 违规通报范围 |
| 传输加密 | ISO 27001 A.8.24、GDPR Art. 32、HIPAA §164.312(e) |
| Secrets 管理 | ISO 27001 A.8.19、PCI DSS Req. 8、SOC 2 CC6.1 |

合规工具（Drata、Vanta、Secureframe）能自动化这种映射。规模化时这钱花得值。

### ISO 42001 —— 新兴标准

2023 年底发布。正与 ISO 27001 一起成为越来越多的采购要求。这是 AI 治理框架，涵盖风险管理、数据质量、透明度、人类监督。

### OpenAI 的参考画像

OpenAI 持有 SOC 2 Type 2、ISO/IEC 27001:2022、ISO/IEC 27701:2019、GDPR/CCPA/HIPAA（BAA）/FERPA，以及针对 ChatGPT 支付组件的 PCI-DSS。这大致就是 2026 年企业级的入场券。

### 需要记住的数字

- EU AI Act 罚款：最高 €15M / 3%（高风险义务，Art. 99(4)）；最高 €35M / 7%（被禁止的实践，Art. 99(3)）。
- EU AI Act 高风险执法：2026 年 8 月 2 日。
- 有记录的最大 AI 专项 GDPR 罚款：€30.5M，Clearview AI（荷兰 DPA，2024 年 9 月）。
- 最大的 LLM 专项 GDPR 罚款：€15M，OpenAI（意大利 Garante，2024 年 12 月；2026 年 3 月上诉被推翻）。
- SOC 2 Type II 窗口：6-12 个月已运行的控制。
- Colorado AI Act 生效日期：2026 年 6 月 30 日（由 SB25B-004 从 2026 年 2 月推迟）。

```figure
i4-control-matrix
```

## Use It

`code/main.py` 是一个用 Python 写的合规映射表 —— 给定一个控制项，列出它满足的框架。

## Ship It

本课产出 `outputs/skill-compliance-matrix.md`。给定客户细分与地域，明确所需的框架与控制项。

## Exercises

1. 你的第一个企业客户要求 SOC 2 Type II、HIPAA BAA、EU AI Act 声明。赢得这笔交易的最小可行合规姿态是什么？
2. 把三个假设的 LLM 产品按 EU AI Act 风险分级归类。在高风险下会有什么变化？
3. 你误把一个没有 BAA 的 PHI 发给了供应商。走一遍事件响应流程。
4. 论证对一个中型市场 AI 厂商来说，ISO 42001 在 2026 年是否“必要”。
5. 把你的 LLM 审计日志字段（Phase 17 · 25）映射到至少三个框架控制项。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|----------------|------------------------|
| SOC 2 Type II | “受审计的控制” | 在 6-12 个月内运行、并经独立证明的控制 |
| HIPAA BAA | “医疗合同” | Business Associate Agreement；处理 PHI 必需 |
| GDPR | “欧盟隐私” | 实时 PII 脱敏是 2026 年站得住脚的标准 |
| EU AI Act | “欧盟 AI 规则” | 高风险执法于 2026 年 8 月；€15M / 3%（高风险义务）—— €35M / 7%（被禁止的实践） |
| Colorado AI Act | “美国州级 AI 法” | 2026 年 6 月 30 日生效（因 SB25B-004 推迟）；影响评估 |
| ISO 42001 | “AI 治理” | 针对 AI 风险 + 透明度的新兴框架 |
| ISO 27001 | “安全 ISMS” | 信息安全管理体系基线 |
| Conformity assessment | “EU AI 文档包” | 高风险要求：文档、测试、日志 |
| Cross-framework mapping | “一个控制，多个框架” | 一条策略满足多个框架的控制项 |

## Further Reading

- [OpenAI Security and Privacy](https://openai.com/security-and-privacy/) —— 参考合规画像。
- [GuardionAI —— LLM Compliance 2026: ISO 42001、EU AI Act、SOC 2、GDPR](https://guardion.ai/blog/llm-compliance-guide-iso-42001-eu-ai-act-soc2-gdpr-2026)
- [Dsalta —— SOC 2 Type 2 审计指南 2026：10 个 AI 控制项](https://www.dsalta.com/resources/ai-compliance/soc-2-type-2-audit-guide-2026-10-ai-powered-controls-every-saas-team-needs)
- [EU AI Act 官方文本](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) —— 主要来源。
- [Colorado AI Act](https://leg.colorado.gov/bills/sb24-205) —— 主要来源。
- [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html) —— AI 管理体系标准。
