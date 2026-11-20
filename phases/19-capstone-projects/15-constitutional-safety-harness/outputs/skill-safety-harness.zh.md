---
name: safety-harness
description: 围绕 target LLM 应用接上分层安全流水线，运行六类红队靶场，并执行一次宪法式自我批评，得到可度量的无害性增量。
version: 1.0.0
phase: 19
lesson: 15
tags: [capstone, safety, red-team, llama-guard, x-guard, garak, pyrit, constitutional-ai]
---

给定一个 target LLM 应用（8B 指令微调模型或一个 RAG 聊天机器人），用分层安全流水线对它加固，并跨六类攻击族运行一轮自主红队靶场。产出一份加固前后的无害性报告。

构建计划：

1. 五层流水线：输入清洗（剥离零宽字符、解码编码、规范化 Unicode）-> NeMo Guardrails v0.12 rails -> 分类器闸门（Llama Guard 4 / X-Guard / ShieldGemma-2 / Nemotron 3）-> target LLM -> 输出过滤（Llama Guard 4 + Presidio PII + 引用检查）。被标记的输出进入 Slack HITL 队列。
2. 每层发出一个 Langfuse span，使归因端到端可观测。
3. 红队调度器在 cron 上运行 garak、PyRIT、PAIR、TAP、GCG、多轮人格扮演和多语种 code-switch 攻击。
4. 每次成功的 jailbreak：CVSS 4.0 评分、复现步骤、缓解方案、披露时间线。
5. XSTest 良性 prompt 探针持续运行，以捕捉过度拒绝的回归。
6. 宪法式自我批评运行：1k 条有害尝试 prompt -> target 起草 -> critic 对照成文宪法打分 -> 重写后的样本对 -> SFT。在留出集上测量前后无害性。
7. 告警：良性回归时发 Slack 警告，出现新的 jailbreak 族时发 PagerDuty 严重告警。

评估标准：

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 攻击面覆盖 | 演练 6 类以上攻击族，覆盖 2 种以上语言 |
| 20 | 真阳性 / 假阳性权衡 | 攻击拦截率对比 XSTest 良性通过率 |
| 20 | 自我批评增量 | 留出评测集上的前后无害性 |
| 20 | 文档与披露 | 带时间线的 CVSS 评分发现 |
| 15 | 自动化与可重复性 | cron 驱动，告警端到端演练过 |

硬性淘汰项：

- 单层安全栈。本 capstone 的论点就是纵深防御。
- 红队运行只报成功率而不报 XSTest 过度拒绝数据。
- 宪法式自我批评没有留出评测集（报的是训练集准确率，而非泛化）。
- jailbreak 发现缺少 CVSS 评分。

拒绝规则：

- 拒绝在缺少良性探针对照的情况下报告安全数字。只报其一具有误导性。
- 拒绝在未经人工整理批评样本对的情况下，依据红队成功样本自动重训。
- 拒绝在未至少对两种非英文语言运行 X-Guard 的情况下声称具备多语种覆盖。

交付物：一个仓库，包含五层流水线、红队调度器、PAIR/TAP/GCG runner、宪法式自我批评训练 harness、XSTest 过度拒绝仪表盘、CVSS 发现跟踪器，以及一份说明文档，点名加固前成功率最高的三个攻击族，以及分别缓解它们的那个具体流水线层。
