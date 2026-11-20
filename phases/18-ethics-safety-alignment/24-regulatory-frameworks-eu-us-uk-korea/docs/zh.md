# 监管框架 — EU、US、UK、Korea

> 四种主要监管制度定义了 2026 年的 AI 治理格局。EU AI Act（2024 年 8 月 1 日生效）——禁止性实践与 AI 素养自 2025 年 2 月 2 日起适用；GPAI 义务自 2025 年 8 月 2 日起适用；全面适用与第 50 条透明度自 2026 年 8 月 2 日起适用；存量 GPAI 与嵌入式 high-risk 系统自 2027 年 8 月 2 日起适用；罚款最高 1500 万欧元或全球营业额的 3%。GPAI Code of Practice（2025 年 7 月 10 日）：三章——Transparency、Copyright、Safety and Security——共 12 项承诺；执法自 2026 年 8 月开始。UK AISI -> AI Security Institute（2025 年 2 月）：更名显示范围收窄。US AISI -> CAISI（2025 年 6 月）：NIST 下属的 Center for AI Standards and Innovation；转向促增长姿态。韩国 AI Framework Act（2024 年 12 月通过，2026 年 1 月生效）：第 12 条在 MSIT 下设 AISI；强制外国 AI 公司设本地代表、风险评估，并对高影响与生成式 AI 采取安全措施。

**Type:** Learn
**Languages:** none
**Prerequisites:** 第 18 阶段，第 18 课（frontier frameworks）、第 27 课（data governance）
**Time:** ~75 分钟

## Learning Objectives

- 描述 EU AI Act 的风险分级（禁止性、high-risk、general-purpose、limited-risk）以及 2025 年 8 月 / 2026 年 8 月 / 2027 年 8 月的时间线。
- 描述 GPAI Code of Practice 的三章，以及每章约束哪些提供者。
- 描述 2025 年的更名：UK AISI -> AI Security Institute；US AISI -> CAISI；每次更名暗示了什么政策方向。
- 陈述韩国 AI Framework Act 的核心条款。

## 问题场景

实验室框架（第 18 课）是自愿性的。监管框架是强制性的。2024-2026 年见证了第一波综合性 AI 监管生效。部署者必须把技术控制映射到监管义务；这种映射因法域而异。

## 核心概念

### EU AI Act

**2024 年 8 月 1 日生效。** 风险分级结构：

- **禁止性实践**（第 5 条）。社会评分、公共场所实时远程生物识别（有执法例外）、对弱势群体的剥削性操纵。自 2025 年 2 月 2 日起适用。
- **High-risk 系统**（附件 III）。就业、教育、信贷、执法、司法、移民。要求 conformity assessment、风险管理、日志记录、透明度。
- **General-Purpose AI (GPAI) 模型**。自 2025 年 8 月 2 日起适用。所有 GPAI 提供者都有义务；systemic-risk GPAI（训练算力 >1e25 FLOP）有额外义务。
- **有限风险系统**。第 50 条下的透明度义务（AI 生成内容标注）。自 2026 年 8 月 2 日起适用。

时间线：
- 2025 年 2 月 2 日：禁止性实践 + AI 素养。
- 2025 年 8 月 2 日：GPAI + 治理。
- 2026 年 8 月 2 日：全面适用 + 第 50 条透明度 + 罚款最高 1500 万欧元 / 全球营业额 3%。
- 2027 年 8 月 2 日：存量 GPAI + 嵌入式 high-risk。

委员会在 2025 年末提议把 high-risk 时间线调整为 16 个月。

### GPAI Code of Practice

2025 年 7 月 10 日发布。三章：

- **Transparency。** 所有 GPAI 提供者。
- **Copyright。** 所有 GPAI 提供者。
- **Safety and Security。** systemic-risk GPAI 提供者（估计 5-15 家公司）。

共 12 项承诺。由 AI Office 主持的 Signatory Taskforce 管理实施。执法自 2026 年 8 月 2 日开始；在此之前接受善意合规。

### 第 50 条的透明度准则

首版草案 2025 年 12 月 17 日。第二版草案 2026 年 3 月。定稿 2026 年 6 月。覆盖包括 deepfake 在内的 AI 生成内容标注——这是要求第 23 课水印技术的监管层。

### UK AI Security Institute（2025 年 2 月）

由 AI Safety Institute 更名而来。更名收窄了范围：放弃算法 bias 与言论自由的框架；聚焦前沿能力安全。开源了 Inspect 评估工具（2024 年 5 月）。与 Redwood（第 10 课）合作开展 control 安全案例。

### US CAISI（2025 年 6 月）

特朗普政府把 NIST 的 AI Safety Institute 改造为 Center for AI Standards and Innovation。依据副总统 Vance 在巴黎 AI Action Summit 的讲话，转向“促增长的 AI 政策”。减少对部署前评估的强调；强调标准与创新支持。这是对 EU AI Act 监管姿态的国内制衡。

### 韩国 AI Framework Act

2024 年 12 月通过。2025 年 1 月颁布。2026 年 1 月生效。整合了 19 项独立的 AI 法案。

第 12 条在科学与信息通信部（MSIT）下设 AISI。强制要求：
- 在韩国运营的外国 AI 公司设本地代表。
- 对“高影响”AI 系统做风险评估。
- 对生成式 AI 与高影响 AI 采取安全措施。

首个拥有综合性横向 AI 监管的亚洲法域。

### 跨法域动态

- EU：严格、风险分级、重罚。隐私邻域监管的基准。
- US：偏好创新、去中心化，各州（例如加州 AB 2013——第 27 课）填补联邦空白。
- UK：狭窄的安全聚焦、强大的评估基础设施。
- Korea：MSIT 主导、聚焦外国提供者。

相互竞争的监管理念。跨法域部署者必须遵守最严格者，而 2026 年最严格的通常是 EU AI Act。

### 本课在 Phase 18 中的位置

第 18 课是实验室自愿治理；第 24 课是监管；第 25 课是 AI 系统的一类新兴 CVE；第 26 至 27 课覆盖文档（卡片）与训练数据治理。

```figure
an-eu-act-timeline
```

## Use It

无代码。阅读 EU AI Act 的一手材料：法规文本、GPAI Code of Practice、UK AISI 的 Inspect 框架。把你的部署映射到各法域适用的义务。

## Ship It

本课产出 `outputs/skill-regulatory-map.md`。给定一段部署描述，它映射适用法域、各法域中的分级归类、逐法域义务以及截止时间结构。

## Exercises

1. 阅读 EU AI Act（Regulation 2024/1689）与 GPAI Code of Practice（2025 年 7 月 10 日）。指出适用于每个 GPAI 提供者的三项义务，以及仅适用于 systemic-risk GPAI 的三项义务。

2. 一个部署由美国公司做出、运行在欧盟基础设施上、服务韩国用户。哪三个法域的规则适用？在每个实质问题上哪条规则具有约束力？

3. UK AI Security Institute 的更名收窄了范围。支持并反对这种更窄的框定。指出每种立场依赖的政策假设。

4. CAISI 的“促增长”框架偏离了 2022-2024 年的 AI 安全研究所模式。指出这一框架会带来的两项可测量的政策转变。

5. 韩国 AI Framework Act 要求外国提供者设本地代表。描述这对一家服务韩国用户的湾区公司的运营含义。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| EU AI Act | “那条法规” | 基于风险分级的横向 AI 监管；2024 年 8 月生效 |
| GPAI | “general-purpose AI” | 大型基础模型；systemic-risk 子集有额外义务 |
| Article 50 | “透明度义务” | AI 生成内容标注；2026 年 8 月适用 |
| UK AISI | “AI Security Institute” | 2025 年 2 月更名；更窄的前沿安全聚焦 |
| CAISI | “美国 AI 标准中心” | 2025 年 6 月由 AI Safety Institute 更名；促增长姿态 |
| Korean AI Framework Act | “MSIT 横向监管” | 首个亚洲综合性 AI 法律；2026 年 1 月生效 |
| Systemic-risk GPAI | “1e25 FLOP 阈值” | 额外义务层级；估计约束 5-15 家公司 |

## Further Reading

- [EU AI Act 文本（Regulation 2024/1689）](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) —— 法规与时间线
- [GPAI Code of Practice（2025 年 7 月 10 日）](https://digital-strategy.ec.europa.eu/en/library/final-version-general-purpose-ai-code-practice) —— 三章准则
- [UK AI Security Institute（2025 年 2 月更名）](https://www.gov.uk/government/organisations/ai-security-institute) —— 官方页面
- [CSET — 韩国 AI Framework Act 分析（2025）](https://cset.georgetown.edu/publication/south-korea-ai-law-2025/) —— 韩国框架分析
