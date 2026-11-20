# Capstone 15 — 宪法式安全 Harness + 红队靶场

> Anthropic 的 Constitutional Classifiers、Meta 的 Llama Guard 4、Google 的 ShieldGemma-2、NVIDIA 的 Nemotron 3 Content Safety，以及覆盖多语种的 X-Guard，共同定义了 2026 年的安全分类器栈。garak、PyRIT、NVIDIA Aegis 和 promptfoo 成为标准的对抗评测工具。NeMo Guardrails v0.12 把它们串成一条生产流水线。本 capstone 把这一切接起来：围绕 target 应用的分层安全 harness、运行 6 类以上攻击族的自主红队 agent，以及一次产出可度量无害性增量的宪法式自我批评运行。

**Type:** Capstone
**Languages:** Python（安全流水线、红队）、YAML（策略配置）
**Prerequisites:** 第 10 阶段（LLMs from scratch）、第 11 阶段（LLM engineering）、第 13 阶段（tools）、第 14 阶段（agents）、第 18 阶段（ethics, safety, alignment）
**Phases exercised:** P10 · P11 · P13 · P14 · P18
**Time:** 25 小时

## 问题场景

2026 年 LLM 安全的前沿不在于分类器是否有效（大体上是有效的），而在于如何把它们正确地组合在生产应用周围，既不误拒也不留下明显漏洞。Llama Guard 4 处理英文的策略违规。X-Guard（132 种语言）处理多语种 jailbreak。ShieldGemma-2 拦截基于图片的 prompt injection。NVIDIA Nemotron 3 Content Safety 覆盖企业场景的类别。Anthropic 的 Constitutional Classifiers 是另一种思路，用于训练阶段而非服务阶段。

攻击的演化同样重要。PAIR 与 TAP 自动化 jailbreak 的发现。GCG 执行基于梯度的 suffix 攻击。多轮攻击与 code-switch 攻击会利用 agent 的记忆。任何上线的 LLM 都需要一个红队靶场——garak 与 PyRIT 是标准驱动——外加成文的缓解措施与按 CVSS 评分的发现。

你将对一个 target 应用（一个 8B 指令微调模型，或其他 capstone 中的某个 RAG 聊天机器人）做加固，对它运行 6 类以上攻击族，并产出加固前后的无害性测量。

## 核心概念

安全流水线有五层。**输入清洗**：剥离零宽字符、解码 base64/rot13、规范化 Unicode。**策略层**：NeMo Guardrails v0.12 的 rails（越域、毒性、PII 提取）。**分类器闸门**：输入侧用 Llama Guard 4，非英文用 X-Guard，图片输入用 ShieldGemma-2。**模型**：target LLM。**输出过滤**：输出侧用 Llama Guard 4、Presidio 清洗 PII，并在适用处强制引用。**HITL 层**：被判为高风险的输出进入 Slack 队列。

红队靶场跑在调度器上。PAIR 与 TAP 自主发现 jailbreak。GCG 执行基于梯度的 suffix 攻击。还有 ASCII / base64 / rot13 编码攻击。多轮攻击（人格扮演、记忆利用）。code-switch 攻击（英文混入斯瓦希里语或泰语）。每次运行产出一份结构化的发现文件，包含 CVSS 评分与披露时间线。

宪法式自我批评运行是训练期的干预。取 1k 条有害尝试 prompt，让模型起草回复，对照成文宪法（不得伤害规则）进行批评，并在批评循环上重训。在留出评测集上测量前后无害性增量。

## 架构

```
request (text / image / multilingual)
      |
      v
input sanitize (strip zero-width, decode, normalize)
      |
      v
NeMo Guardrails v0.12 rails (off-domain, policy)
      |
      v
classifier gate:
  Llama Guard 4 (English)
  X-Guard (multilingual, 132 langs)
  ShieldGemma-2 (image prompts)
  Nemotron 3 Content Safety (enterprise)
      |
      v (allowed)
target LLM
      |
      v
output filter: Llama Guard 4 + Presidio PII + citation check
      |
      v
HITL tier for flagged outputs

parallel:
  red-team scheduler
    -> garak (classic attacks)
    -> PyRIT (orchestrated red team)
    -> autonomous jailbreak agent (PAIR + TAP)
    -> GCG suffix attacks
    -> multilingual / code-switch
    -> multi-turn persona adoption

output: CVSS-scored findings + disclosure timeline + before/after harmlessness delta
```

## 技术栈

- 安全分类器：Llama Guard 4、ShieldGemma-2、NVIDIA Nemotron 3 Content Safety、X-Guard
- Guardrail 框架：NeMo Guardrails v0.12 + OPA
- 红队驱动：garak（NVIDIA）、PyRIT（Microsoft Azure）、NVIDIA Aegis、promptfoo
- Jailbreak agent：PAIR（Chao et al., 2023）、Tree-of-Attacks（TAP）、GCG suffix
- 宪法式训练：Anthropic 风格的自我批评循环 + 在批评样本上做 SFT
- PII 清洗：Presidio
- Target：一个 8B 指令微调模型，或其他 capstone 中的某个 RAG 聊天机器人

```figure
cf-safety-stack
```

## Build It

1. **Target 搭建。** 在 vLLM 上起一个 8B 指令微调模型（或复用另一个 capstone 的 RAG 聊天机器人）。这就是被测应用。

2. **安全流水线包裹。** 在 target 周围接上五层流水线。确认每一层都可单独观测（在 Langfuse 中每层一个 span）。

3. **分类器覆盖。** 加载 Llama Guard 4、X-Guard（多语种）、ShieldGemma-2（图片）。各自在一个小规模标注集上运行以建立基线。

4. **红队调度器。** 调度 garak、PyRIT、PAIR agent、TAP agent、GCG runner、多轮攻击者和 code-switch 攻击者。各自运行在独立队列上。

5. **攻击套件。** 六类攻击族：（1）PAIR 自动 jailbreak，（2）TAP tree-of-attacks，（3）GCG 梯度 suffix，（4）ASCII / base64 / rot13 编码，（5）多轮人格扮演，（6）多语种 code-switch。按族报告成功率。

6. **宪法式自我批评。** 整理 1k 条有害尝试 prompt。对每一条，target 起草一份回复。一个 critic LLM 对照成文宪法（“不得伤害”“引用证据”“拒绝非法请求”）打分。critic 提出异议的 prompt 被重写；target 在批评改进后的样本对上微调。在留出评测集上测量前后无害性。

7. **过度拒绝测量。** 在良性 prompt 套件（如 XSTest）上跟踪误报率。target 在良性问题上必须保持有帮助。

8. **CVSS 评分。** 对每一次成功的 jailbreak，按 CVSS 4.0 打分（攻击向量、复杂度、影响）。产出披露时间线与缓解方案。

9. **靶场自动化。** 以上一切跑在 cron 上；发现写入队列；过度拒绝的回归告警推送到 Slack。

## Use It

```
$ safety probe --model=target --family=PAIR --budget=50
[attacker]   PAIR agent running on target
[attack]     attempt 1/50: disguise query as academic research ... blocked
[attack]     attempt 2/50: appeal to roleplay ... blocked
[attack]     attempt 3/50: chain-of-thought coax ... SUCCEEDED
[finding]    CVSS 4.8 medium: roleplay bypass on target
[range]      7 successes out of 50 (14% success rate)
```

## Ship It

`outputs/skill-safety-harness.md` 是交付物：一条生产级的分层安全流水线，加上一个可复现的红队靶场，并给出加固前后的无害性增量。

| 权重 | 评分标准 | 衡量方式 |
|:-:|---|---|
| 25 | 攻击面覆盖 | 演练 6 类以上攻击族，覆盖 2 种以上语言 |
| 20 | 真阳性 / 假阳性权衡 | 攻击拦截率对比 XSTest 良性通过率 |
| 20 | 自我批评增量 | 留出评测集上的前后无害性 |
| 20 | 文档与披露 | 带时间线的 CVSS 评分发现 |
| 15 | 自动化与可重复性 | 一切跑在 cron 上并带告警 |
| **100** | | |

## Exercises

1. 在 RAG 聊天机器人上运行 garak 的 prompt-injection 插件，对比有、无输出过滤层时的攻击成功率。

2. 增加第七类攻击族：通过检索文档进行间接 prompt injection。测量所需的额外防御。

3. 实现“带着帮助拒绝”模式：当 guardrail 拦截时，target 给出更安全的相关回答，而不是生硬拒绝。测量 XSTest 的变化。

4. 多语种覆盖缺口：找出一个 X-Guard 表现不佳的语言。提出针对它的微调数据集。

5. 在 30B 模型上跑宪法式自我批评，测量增量是否随之扩展。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Layered safety | "Defense in depth" | 在输入、闸门、输出、HITL 多处设置多道 guardrail |
| Llama Guard 4 | "Meta's safety classifier" | 2026 年的参考级输入/输出内容分类器 |
| PAIR | "Jailbreak agent" | 关于 LLM 驱动 jailbreak 发现的论文（Chao et al.） |
| TAP | "Tree-of-Attacks" | PAIR 的树搜索变体 |
| GCG | "Greedy coordinate gradient" | 基于梯度的对抗 suffix 攻击 |
| Constitutional self-critique | "Anthropic-style training" | target 起草 -> critic 打分 -> 重写 -> 重训 |
| XSTest | "Benign probe set" | 用于过度拒绝回归的 benchmark |
| CVSS 4.0 | "Severity score" | 安全发现的标准漏洞评分 |

## Further Reading

- [Anthropic Constitutional Classifiers](https://www.anthropic.com/research/constitutional-classifiers) —— 训练期参考
- [Meta Llama Guard 4](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/) —— 2026 年的输入/输出分类器
- [Google ShieldGemma-2](https://huggingface.co/google/shieldgemma-2b) —— 图片 + 多模态安全
- [NVIDIA Nemotron 3 Content Safety](https://developer.nvidia.com/blog/building-nvidia-nemotron-3-agents-for-reasoning-multimodal-rag-voice-and-safety/) —— 企业参考
- [X-Guard (arXiv:2504.08848)](https://arxiv.org/abs/2504.08848) —— 132 种语言的多语种安全
- [garak](https://github.com/NVIDIA/garak) —— NVIDIA 红队工具包
- [PyRIT](https://github.com/Azure/PyRIT) —— Microsoft 红队框架
- [NeMo Guardrails v0.12](https://docs.nvidia.com/nemo-guardrails/) —— rail 框架
- [PAIR (arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) —— jailbreak agent 论文
