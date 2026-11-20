# Model Card、System Card 与 Dataset Card

> 三种文档格式构成了 AI 透明度的结构。Model Cards（Mitchell 等，2019）——模型的营养标签：训练数据、量化的分群分析、伦理考量、注意事项；而 Hugging Face 上只有 0.3% 的 model card 记录了伦理考量（Oreamuno 等，2023）。Datasheets for Datasets（Gebru 等，2018，CACM）——动机、构成、采集过程、标注、分发、维护；类比电子元件的数据手册。Data Cards（Pushkarna 等，Google 2022）——模块化分层细节（telescopic、periscopic、microscopic），作为面向多元读者的边界物（boundary object）。2024-2025 年的进展：借助 LLM 自动生成（CardGen，Liu 等，2024）；model card 的细节程度与 HF 上最高 29% 的下载量增长相关（Liang 等，2024）；可验证的声明证明（Laminator，Duddu 等，2024）；新增碳/水足迹的可持续性报告（Jouneaux 等，2025 年 7 月）；EU/ISO 监管卡正在成形。System Cards（Sidhpurwala 2024；Meta 的系统级透明度工作；"Blueprints of Trust" arXiv:2509.20394）——端到端 AI 系统文档，覆盖安全能力、prompt-injection 防护、数据外泄检测、与人类价值观的对齐。

**Type:** Build
**Languages:** Python（stdlib，model card + datasheet + system card 生成器）
**Prerequisites:** 第 18 阶段，第 18 课（safety frameworks）、第 24 课（regulatory）
**Time:** ~60 分钟

## Learning Objectives

- 描述 Mitchell 等 2019 的原始 model card 与 Gebru 等 2018 的 datasheet。
- 描述 Data Cards 的 telescopic/periscopic/microscopic 分层。
- 描述 System Cards 及其端到端覆盖范围。
- 说出三项 2024-2025 年的进展（自动生成、可验证声明证明、可持续性报告）。

## 问题场景

监管框架（第 24 课）与实验室安全政策（第 18 课）都要求提供文档。文档格式从面向模型（model cards）演进到面向数据集（datasheets），再到面向系统（system cards）。每种格式处理不同范围的透明度。2024-2025 年的自动化与可验证声明证明工作，则针对长期存在的采用率问题。

## 核心概念

### Model Cards（Mitchell 等，2019）

章节：
- 模型细节。
- 预期用途。
- 因素（评估时相关的统计或环境因素）。
- 指标。
- 评估数据。
- 训练数据。
- 量化分析（按因素分群）。
- 伦理考量。
- 注意事项与建议。

采用率问题：Oreamuno 等 2023 对 Hugging Face model cards 的审计发现，只有 0.3% 记录了伦理考量。

### Datasheets for Datasets（Gebru 等，2018）

类比电子元件的数据手册。章节：
- 动机（为什么创建该数据集）。
- 构成（其中包含什么）。
- 采集过程（如何组装）。
- 标注（如适用）。
- 用途（预期、禁止、风险）。
- 分发。
- 维护。

发表于 CACM 2021。datasheet 是上游文档；model card 的可靠性取决于 datasheet 是否准确。

### Data Cards（Pushkarna 等，Google 2022）

模块化分层细节。三个缩放层级：
- **Telescopic。** 面向非专家的高层摘要。
- **Periscopic。** 面向 ML 从业者的中层概览。
- **Microscopic。** 面向审计者的细粒度特征级文档。

边界物（boundary object）视角：不同的读者从同一份文档中提取不同的信息。

### System Cards

范围：端到端 AI 系统，包括模型 + safety stack + 部署环境。章节通常包括：
- 安全能力。
- Prompt-injection 防护。
- 数据外泄检测。
- 与所声明的人类价值观的对齐。
- 事件响应。

Sidhpurwala 2024 与 Meta 的系统级透明度工作。"Blueprints of Trust"（arXiv:2509.20394）把 System Card 正式定义为 Model Card 在部署层的补充。

### 2024-2025 年的进展

- **CardGen（Liu 等，2024）。** 借助 LLM 自动生成 model card；报告称在 Mitchell 2019 标准化字段上，其客观性高于许多人工撰写的卡。
- **下载相关性（Liang 等，2024）。** 细节详尽的 model card 与 HF 上最高高出 29% 的下载率相关——采用压力如今来自市场，而不只是合规。
- **Laminator（Duddu 等，2024）。** 通过硬件 TEE / 密码学签名实现可验证的声明证明——让 model card 携带 claim 的证明，而不只是 claim。
- **可持续性（Jouneaux 等，2025 年 7 月）。** 新增碳、水与计算能耗足迹；正在成形的 ISO 标准。
- **监管卡。** EU AI Act（第 24 课）的 GPAI Code of Practice 透明度章节要求把 model card 作为合规产物。

### 它在第 18 阶段中的位置

第 24-25 课是监管与 CVE 层。第 26 课是文档层。第 27 课是训练数据治理，也就是 datasheet 的上游。第 28 课是产出卡中所引用评估的研究生态。

```figure
an-card-scopes
```

## Use It

`code/main.py` 为一个玩具部署生成一份最小化的 model card、datasheet 与 system card。每份都遵循经典章节结构。你可以检视其格式并比较三种范围。

## Ship It

本课产出 `outputs/skill-card-audit.md`。给定一份 model card、datasheet 或 system card，它会审计章节覆盖度、数值分群以及是否存在可验证的声明证明。

## Exercises

1. 运行 `code/main.py`。检视生成的各份卡。指出哪些章节薄弱（仅有占位符），并说明什么样的证据能加强它们。

2. 为 model card 扩展一项跨两个统计群体的量化分群分析（第 20 课）。

3. 阅读 Oreamuno 等 2023 关于 0.3% 采用率的研究。提出一项对 model card 规范的结构性修改，以提升伦理考量的采用率。

4. Laminator（Duddu 等，2024）使用 TEE 实现可验证的声明证明。设计一个 model-card 字段，携带某项评估结果的密码学证明，并描述验证者所扮演的角色。

5. 为你过去的一个项目或一个假想的部署撰写一份 System Card（是 System Card，不是 Model Card）。指出对第三方审计者价值最高的章节。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Model Card | "the Mitchell card" | Mitchell 等 2019 提出的 ML 模型标准文档 |
| Datasheet | "the Gebru datasheet" | Gebru 等 2018 提出的数据集标准文档 |
| Data Card | "the Pushkarna card" | Google 2022 提出的模块化分层数据文档 |
| System Card | "the deployment card" | 包含 safety stack 的端到端 AI 系统文档 |
| Boundary object | "different readers, one doc" | Data Cards 的视角：同一份文档服务多元受众 |
| Verifiable attestation | "the Laminator attestation" | 附加在文档声明之上的密码学或 TEE 证明 |
| Sustainability field | "carbon / water footprint" | 2025 年新增的环境核算字段 |

## Further Reading

- [Mitchell 等 — Model Cards for Model Reporting（arXiv:1810.03993，FAT* 2019）](https://arxiv.org/abs/1810.03993) —— 经典的 model card
- [Gebru 等 — Datasheets for Datasets（CACM 2021，arXiv:1803.09010）](https://arxiv.org/abs/1803.09010) —— datasheet 论文
- [Pushkarna 等 — Data Cards（Google 2022）](https://arxiv.org/abs/2204.01075) —— 分层数据文档
- [Sidhpurwala 等 — Blueprints of Trust（arXiv:2509.20394）](https://arxiv.org/abs/2509.20394) —— System Card 的正式化
