# Capstone 17 — 个人 AI 导师（自适应、多模态、带记忆）

> Khanmigo（Khan Academy）、Duolingo Max、Google LearnLM / Gemini for Education、Quizlet Q-Chat 和 Synthesis Tutor 都在 2026 年大规模上线了自适应多模态辅导。共同形态是：苏格拉底式策略（绝不直接倒出答案）、每次交互后都会更新的 learner model（贝叶斯知识追踪风格）、语音 + 文字 + 拍照解题输入、课程图检索、间隔重复调度，以及针对适龄内容的严格安全过滤。本 capstone 要求交付一个特定学科的导师（K-12 代数或 Python 入门），与 10 名学习者进行为期两周的成效研究，并通过内容安全审计。

**Type:** Capstone
**Languages:** Python（后端、learner model）、TypeScript（Web 应用）、SQL（通过 Postgres + Neo4j 的课程图）
**Prerequisites:** 第 5 阶段（NLP）、第 6 阶段（speech）、第 11 阶段（LLM engineering）、第 12 阶段（multimodal）、第 14 阶段（agents）、第 17 阶段（infrastructure）、第 18 阶段（safety）
**Phases exercised:** P5 · P6 · P11 · P12 · P14 · P17 · P18
**Time:** 30 小时

## 问题场景

自适应辅导曾是教育科技的研究细分领域。到 2026 年它已是消费级产品。Khanmigo 部署在大多数美国学区。Duolingo Max 的 MAU 达到数千万。Google 的 LearnLM / Gemini for Education 为 Google Classroom 中的辅导提供支持。Quizlet Q-Chat 与抽认卡并存。Synthesis Tutor 凭“为好奇孩子请的导师”走红。共同要素是：多模态输入（打字、说话、拍摄方程）、苏格拉底式教学法（先提问、后解释）、每次交互后更新的 learner model，以及严格的适龄安全。

你要为某个特定群体构建其中一个。衡量标准是一场真实的成效研究：为期两周、10 名学习者的前测与后测分数。语音循环必须自然（capstone 03 的子栈）。记忆必须尊重隐私。安全过滤必须通过面向 K-12 的、具备 COPPA 意识的红队测试。

## 核心概念

四个组件。**Tutor policy** 是一个苏格拉底式循环：当学习者索要答案时，策略改问一个引导性问题；当他们答对时，进入下一个概念；当他们卡住时，给出分层的提示。**Learner model** 是贝叶斯知识追踪（或一个简单变体），在每次交互后更新每个课程节点的掌握概率。**课程图**是一个由概念与先修边构成的 Neo4j 图；策略沿图行走以挑选下一个概念。**记忆**是一个情节 + 语义存储（agentmemory 风格），保存过往交互、错误与偏好。

UX 是多模态的。文字输入用于键入答案。语音输入经由 LiveKit + Whisper（复用 capstone 03）。拍照输入用于数学题，经由 dots.ocr 或 PaliGemma 2。语音输出经由 Cartesia Sonic-2。安全使用 Llama Guard 4 加上适龄过滤器（拦截成人内容、暴力、自我伤害），以及具备 COPPA 意识的记忆保留策略。

成效研究就是交付物。10 名学习者，前测与后测，为期两周。报告学习增益增量与置信区间。与非自适应基线（同样的内容以线性方式投递、不经过 tutor policy）对比。

## 架构

```
learner device
  |
  +-- text         -> web app
  +-- voice        -> LiveKit Agents (ASR + TTS)
  +-- photo math   -> dots.ocr / PaliGemma 2
       |
       v
  tutor policy (LangGraph)
       - Socratic decision head
       - next-concept chooser (curriculum graph walk)
       - hint scaffolder
       - mastery update
       |
       v
  learner model (BKT / item-response theory)
       - per-concept mastery probability
       - spaced-repetition scheduler (SM-2 or FSRS)
       |
       v
  memory (agentmemory-style)
       - episodic: every interaction
       - semantic: learned mistakes, preferences
       - retention policy: COPPA / GDPR aware
       |
       v
  curriculum graph (Neo4j)
       - prerequisite edges
       - OER content attached
       |
       v
  safety:
    Llama Guard 4 + age-appropriate filter
    memory access guarded by learner ID scope
```

## 技术栈

- 学科选择：K-12 代数或 Python 入门（选一个做深）
- Tutor policy：基于 Claude Sonnet 4.7 的 LangGraph（带 prompt caching）
- Learner model：贝叶斯知识追踪（经典）或用于间隔的 FSRS
- 课程图：概念 + 先修边 + OER 内容的 Neo4j
- 记忆：agentmemory 风格的持久化向量 + 情节 + 语义存储
- 语音：LiveKit Agents 1.0 + Cartesia Sonic-2（复用 capstone 03 子栈）
- 拍照解题：dots.ocr 或 PaliGemma 2 用于方程识别
- 安全：Llama Guard 4 + 自研适龄过滤器
- 评测：Bloom 层级问题生成、前/后测 harness、成效研究工具

```figure
cf-tutor-loop
```

## Build It

1. **课程图。** 用 Neo4j 构建 50-150 个概念节点（例如从“数轴”到“二次公式”的 K-12 代数），带先修边。为每个节点附上 OER 内容（Open Textbook、OpenStax）。

2. **Learner model。** 用先验初始化贝叶斯知识追踪：guess、slip、learn-rate。每次交互后更新每个概念的掌握度。按学习者持久化。

3. **Tutor policy。** LangGraph 节点：`read_signal`（学习者的回答是对、部分对还是卡住？）、`select_concept`（遍历课程图挑选优先级最高的概念）、`scaffold`（苏格拉底式 prompt）、`update_mastery`。

4. **记忆。** 每次交互写入情节存储。错误与偏好提升为语义记忆。具备 COPPA 意识的保留策略：1 年后自动删除，家长可访问。

5. **语音路径。** 挂接 tutor policy 的 LiveKit Agents worker。ASR 用 Whisper-v3-turbo。TTS 用 Cartesia Sonic-2。支持打断（复用 capstone 03 的机制）。

6. **拍照解题路径。** 上传或拍摄图片；运行 dots.ocr 或 PaliGemma 2 识别方程；作为结构化输入送入 tutor。

7. **安全。** 每个模型输出都经过 Llama Guard 4 + 适龄过滤器（拦截自我伤害、成人内容、暴力）。记忆访问按 learner ID 限定作用域；提供家长访问入口以执行删除。

8. **成效研究。** 10 名学习者，前测（标准化的 30 题基线），两周的 tutor 交互（每周 3 次），后测。与同一内容的 10 名学习者组成的非自适应基线组对比。

9. **每周进度报告。** 按学习者自动生成 PDF 摘要，涵盖探索的主题、掌握度轨迹与建议的下一步。

## Use It

```
learner: "I don't understand why 3x + 6 = 12 means x = 2"
[signal]   stuck
[concept]  'isolating variables' (prerequisite: addition-subtraction-equality)
[scaffold] "what number would you subtract from both sides to start?"
learner: "6"
[signal]   correct
[mastery]  addition-subtraction-equality: 0.62 -> 0.77
[concept]  continue 'isolating variables'
[scaffold] "great. now what is 3x / 3 equal to?"
```

## Ship It

`outputs/skill-ai-tutor.md` 是交付物：一个特定学科的自适应导师，具备多模态输入、learner model、记忆、安全，以及实测的成效。

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 学习增益增量 | 10 名学习者两周研究中的前/后测增量 |
| 20 | 苏格拉底式忠实度 | 对话样本的评分量表得分 |
| 20 | 多模态 UX | 语音 + 拍照 + 文字的端到端一致性 |
| 20 | 安全与隐私态势 | Llama Guard 4 通过率 + 具备 COPPA 意识的保留策略 |
| 15 | 课程广度与图质量 | 概念覆盖 + 先修图一致性 |
| **100** | | |

## Exercises

1. 在有、无自适应 learner model（随机概念顺序）两种条件下做成效研究。报告增量。预期自适应会胜出，但关键在于差距有多大。

2. 增加多模态探针：同一道概念题分别以文字、语音、拍照三种方式呈现。测量学习者是否用自己偏好的模态时收敛更快。

3. 构建家长仪表盘：练习过的主题、掌握度轨迹、即将学习的概念、安全事件（任何 guardrail 命中）。对齐 COPPA。

4. 增加语言切换模式：tutor 接受西班牙语输入并用西班牙语教学。测量 X-Guard 的覆盖。

5. 压力测试记忆隐私：验证即使通过语音片段重摄取攻击，学习者 A 也无法看到学习者 B 的数据。记录该访问尝试并告警。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Socratic policy | "Ask, do not dump" | tutor 提出引导性问题，而不是直接给出答案 |
| Bayesian knowledge tracing | "BKT" | 计算每个概念掌握概率的经典 learner model 方程 |
| FSRS | "Free Spaced Repetition Scheduler" | 2024 年的间隔重复调度器，优于 SM-2 |
| Curriculum graph | "Concept DAG" | 由概念与先修边构成的 Neo4j 图 |
| Episodic memory | "Per-interaction log" | 每次交互都被存储以供日后检索 |
| Semantic memory | "Learned pattern store" | 从情节记忆提升而来的、压缩后的错误与偏好 |
| COPPA | "Kids privacy law" | 限制收集 13 岁以下儿童数据的美国法律 |

## Further Reading

- [Khanmigo (Khan Academy)](https://www.khanmigo.ai) —— 消费级 K-12 导师参考
- [Duolingo Max](https://blog.duolingo.com/duolingo-max/) —— 语言学习导师参考
- [Google LearnLM / Gemini for Education](https://blog.google/products-and-platforms/products/education/google-learnlm-gemini-generative-ai/) —— 托管参考模型
- [Quizlet Q-Chat](https://quizlet.com) —— 另一参考
- [Synthesis Tutor](https://www.synthesis.com) —— 初创公司参考
- [FSRS algorithm](https://github.com/open-spaced-repetition/fsrs4anki) —— 间隔重复调度器
- [Bayesian Knowledge Tracing](https://en.wikipedia.org/wiki/Bayesian_knowledge_tracing) —— 经典 learner model
- [LiveKit Agents](https://github.com/livekit/agents) —— 语音栈
