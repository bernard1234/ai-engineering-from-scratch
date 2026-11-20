---
name: ai-tutor
description: 为特定学科交付一个自适应多模态个人导师，具备贝叶斯知识追踪、课程图、安全过滤，以及一场可度量的两周成效研究。
version: 1.0.0
phase: 19
lesson: 17
tags: [capstone, tutor, adaptive, bkt, fsrs, livekit, multimodal, coppa]
---

给定一个学科（K-12 代数或 Python 入门），构建一个个人导师，支持文字 + 语音 + 拍照解题输入、贝叶斯知识追踪 learner model、课程图驱动的概念选择、具备 COPPA 意识的记忆与安全过滤。与 10 名学习者进行为期两周的成效研究。

构建计划：

1. Neo4j 中的课程图：50-150 个概念节点，带先修边并附上 OER 内容（OpenStax、Open Textbook）。
2. Learner model：贝叶斯知识追踪，为每个概念法设置 guess/slip/learn-rate 先验；按学习者持久化状态。
3. Tutor policy（基于 Claude Sonnet 4.7 并启用 prompt caching 的 LangGraph）：read_signal -> select_concept（图遍历）-> scaffold（苏格拉底式）-> update_mastery。
4. 记忆：agentmemory 风格的持久化情节 + 语义存储；具备 COPPA 意识的 1 年后自动删除；家长可访问的删除入口。
5. 语音：带 Whisper-v3-turbo ASR 与 Cartesia Sonic-2 TTS 的 LiveKit Agents worker；复用 capstone 03 流水线。
6. 拍照解题：dots.ocr 或 PaliGemma 2 用于方程识别；把结构化输入送入 tutor。
7. 安全：Llama Guard 4 输入/输出；适龄过滤器拦截自我伤害/成人/暴力；按学习者隔离记忆。
8. 每位学习者每周一份 PDF 进度报告。
9. 成效研究：10 名学习者，前测（标准化的 30 题基线），两周的会话（每周 3 次），后测；与非自适应线性对照组对比。

评估标准：

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 学习增益增量 | 10 名学习者两周研究中的前/后测增量 |
| 20 | 苏格拉底式忠实度 | 对话样本的评分量表得分 |
| 20 | 多模态 UX | 语音 + 拍照 + 文字的端到端一致性 |
| 20 | 安全与隐私态势 | Llama Guard 4 通过率 + 具备 COPPA 意识的保留策略 + 跨学习者隔离 |
| 15 | 课程广度与图质量 | 概念覆盖 + 先修图一致性 |

硬性淘汰项：

- 直接倒答案而不提下一个问题的 tutor policy。苏格拉底式是硬性要求。
- 不随每次交互更新的 learner model。BKT 是下限。
- 缺少具备 COPPA 意识保留策略的记忆。对 K-12 受众不可接受。
- 没有非自适应对照组的成效声明。

拒绝规则：

- 拒绝在输入与输出两侧都未部署 Llama Guard 4 的情况下上线。
- 拒绝在缺少家长可访问删除入口的情况下持久化学习者数据。
- 拒绝在未同时运行非自适应基线的情况下声称“自适应”。

交付物：一个仓库，包含课程图、BKT learner model、LangGraph tutor policy、多模态输入处理器、LiveKit 语音流水线、安全流水线、家长仪表盘、成效研究 runner、前/后测 harness，以及一份说明文档，记录相对线性基线的学习增益增量及其置信区间。
