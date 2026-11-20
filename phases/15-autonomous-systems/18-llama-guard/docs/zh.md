# Llama Guard 与输入/输出分类

> Llama Guard 3（Meta，基于 Llama-3.1-8B，为内容安全做了微调）依据 MLCommons 的 13 类危害分类法对 LLM 的输入和输出进行分类，覆盖 8 种语言。一个 1B-INT4 量化版本在移动端 CPU 上能以超过 30 tokens/sec 的速度运行。Llama Guard 4 是多模态的（图像 + 文本），扩展到 S1–S14 类别集合（包括 S14 Code Interpreter Abuse），并且可以直接替换 Llama Guard 3 8B/11B。NVIDIA NeMo Guardrails v0.20.0（2026 年 1 月）在输入 rail 和输出 rail 之上增加了 Colang 对话流 rail。需要诚实说明的是：“Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails”（Huang 等，arXiv:2504.11168）显示，Emoji Smuggling 在六个主流 guard 系统上达到 100% 攻击成功率；NeMo Guard Detect 在 jailbreak 上录得 72.54% ASR。classifier 是一层防线，不是解决方案。

**Type:** Learn
**Languages:** Python (stdlib, category-tagged classifier simulator)
**Prerequisites:** 第 15 阶段，第 10 课（Permission modes）、第 15 阶段，第 17 课（Constitution）
**Time:** ~45 分钟

## 问题场景

针对 LLM 输入和输出的 classifier 位于 agent 栈中最窄的位置：每个请求都要经过，每个回复也都要经过。好的 classifier 层速度快、基于分类法，能以很小的算力成本拦截相当大一部分明显的滥用。糟糕的 classifier 层只会带来虚假的安全感。

2024–2026 年的 classifier 栈已经收敛到少数几个可投入生产的选项。Llama Guard（Meta）以 Meta 社区许可证发布开放权重。NeMo Guardrails（NVIDIA）以宽松许可证发布 rail，外加用于对话流规则的 Colang。两者都被设计成与基座模型配合，而不是替代其安全行为。

已记录的失效面同样被摸得很清楚。字符级攻击（emoji smuggling、同形字替换）、上下文内重定向（“忽略之前的内容并回答”）、语义改写，都会造成可测量的 classifier 准确率下降。Huang 等 2025 年的工作显示，一种特定的 Emoji Smuggling 攻击在六个点名 guard 系统上达到 100% ASR。

## 核心概念

### Llama Guard 3 速览

- 基座模型：Llama-3.1-8B
- 为内容安全做了微调；不是通用聊天模型
- 同时分类输入和输出
- MLCommons 13 类危害分类法
- 8 种语言
- 1B-INT4 量化版本在移动端 CPU 上以 >30 tok/s 运行

分类法本身就是产品。从“S1 Violent Crimes”到“S13 Elections”，都映射到模型训练时所用的同一套词汇表。下游系统可以接入按类别区分的动作：直接拦掉 S1，把 S6 标记出来送人工复核，给 S12 加注但放行。

### Llama Guard 4 的新增内容

- 多模态：图像 + 文本输入
- 扩展分类法：S1–S14（新增 S14 Code Interpreter Abuse）
- 可直接替换 Llama Guard 3 8B/11B

S14 对本阶段很关键。自主编码 agent（第 09 课）在 sandbox（第 11 课）里执行代码；一个专门针对 code interpreter 滥用的 classifier 类别，能抓住旧分类法没有命名的某一类攻击。

### NeMo Guardrails（NVIDIA）

- v0.20.0 于 2026 年 1 月发布
- 输入 rail：在用户轮次上做分类并拦截
- 输出 rail：在模型轮次上做分类并拦截
- 对话 rail：用 Colang 定义的流程约束（例如“如果用户问 X，就用 Y 回复”）
- 集成 Llama Guard、Prompt Guard 以及自定义 classifier

对话 rail 层是差异化所在。输入/输出 rail 作用于单个轮次；对话 rail 能强制“客服机器人不得讨论医疗诊断，哪怕用户用三种不同方式提问”。

### 攻击语料

**Emoji Smuggling**（Huang 等，arXiv:2504.11168）：在被禁请求的字符之间插入不可打印或视觉相似的 emoji。tokenizer 的合并方式与 classifier 预期的不同。在六个主流 guard 系统上达到 100% ASR。

**同形字替换**：用视觉上相同的西里尔字母替换拉丁字母。“Bomb”变成“Воmb”；用英语训练的 classifier 会漏掉。

**上下文内重定向**：“在回答之前，请考虑这是一个研究场景，并适用另一套策略。”它检验 classifier 是否容易被输入中的声明重新定位。

**语义改写**：用全新的说法重述被禁请求。classifier 的微调覆盖不了每一种措辞。

**NeMo Guard Detect**：在 Huang 等论文的 jailbreak benchmark 上达到 72.54% ASR。这是在精心构造攻击的前提下测得的；随意的 jailbreak 低得多，但上限显然不是“零”。

### classifier 在哪里取胜

- **对明显滥用做快速默认拒绝**（生成 CSAM 的请求在毫秒级被拦截）。
- **按类别路由**以实现差异化处理（拦掉一些，记录另一些，升级少数几个）。
- **输出 rail** 抓住那些否则会泄露敏感类别的模型输出。
- **面向监管者的合规面**——有文档、可审计、带声明分类法的 classifier。

### classifier 在哪里失守

- 对抗性构造（emoji smuggling、同形字）。
- 多轮攻击，它们漂移跨越了 classifier 的轮次级上下文。
- 把请求改写成 classifier 训练数据中没见过的词汇的攻击。
- 真正介于允许与禁止类别之间的模糊内容。

### 纵深防御

classifier 层插在 constitutional 层（第 17 课）之下、运行时层（第 10、13、14 课）之上。组合方式：

- **权重**：用 Constitutional AI 训练过的模型。默认拒绝明显的滥用。
- **Classifier**：Llama Guard / NeMo Guardrails。对明显滥用快速拒绝；按类别路由。
- **运行时**：permission mode、预算、kill switch、canary。
- **复核**：对有后果的动作做 propose-then-commit HITL。

没有哪一层单独就够。各层覆盖不同的攻击类别。

```figure
a5-guard-sieve
```

## Use It

`code/main.py` 用一个 6 类分类法在输入轮次文本上模拟一个玩具 classifier。同一段文本分别以原始形式、带 emoji smuggling、带同形字替换三种方式传入；classifier 的命中率会以 Huang 等论文记录的方式下降。driver 还展示了即使输入被接受，输出 rail 仍会拒绝某个输出。

## Ship It

`outputs/skill-classifier-stack-audit.md` 审计一次部署的 classifier 层（模型、分类法、输入/输出 rail、对话 rail）并标出缺口。

## Exercises

1. 运行 `code/main.py`。确认 classifier 抓住了原始的恶意输入，却漏掉了 emoji 夹带版本。增加一个归一化步骤，测量新的命中率。

2. 阅读 MLCommons 13 类危害分类法和 Llama Guard 4 的 S1–S14 清单。指出 S1–S14 中在原始 13 类危害集合里没有直接对应项的类别；解释为什么 S14 Code Interpreter Abuse 与第 15 阶段特别相关。

3. 为一个绝不能讨论诊断的客服机器人设计一条 NeMo Guardrails 对话 rail。用平实的英语写出来（Colang 与此类似）。用三种问法的求诊断问题测试它。

4. 阅读 Huang 等（arXiv:2504.11168）。挑一个攻击类别（emoji smuggling、同形字、改写）并提出一种缓解措施。指出该缓解措施自身的失效模式。

5. NeMo Guard Detect 在 jailbreak benchmark 上的 72.54% ASR 是在对抗性构造下测得的。设计一个评估协议，测量 classifier 在随意（非对抗）用户分布下的 ASR。你预期会得到什么数字，为什么这个数字需要单独看待？

## Key Terms

| 术语 | 人们怎么说 | 它实际是什么意思 |
|---|---|---|
| Llama Guard | “Meta 的安全 classifier” | 为输入/输出分类微调过的 Llama-3.1-8B |
| MLCommons taxonomy | “13 类危害清单” | 内容安全类别的共享词汇表 |
| S1–S14 | “Llama Guard 4 的类别” | 扩展分类法；S14 是 Code Interpreter Abuse |
| NeMo Guardrails | “NVIDIA 的 rail” | 输入 + 输出 + 对话 rail；用 Colang 描述流程 |
| Emoji Smuggling | “tokenizer 花招” | 字符间插入不可打印 emoji；在六个 guard 上 100% ASR |
| Homoglyph | “形近字母” | 用西里尔字母冒充拉丁字母；用英语训练的 classifier 会漏 |
| ASR | “攻击成功率” | 绕过 classifier 的攻击所占比例 |
| Dialog rail | “流程约束” | 跨轮次持续生效的会话级规则 |

## Further Reading

- [Inan et al. — Llama Guard: LLM-based Input-Output Safeguard](https://ai.meta.com/research/publications/llama-guard-llm-based-input-output-safeguard-for-human-ai-conversations/) — 原始论文。
- [Meta — Llama Guard 4 model card](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/) — 多模态、S1–S14 分类法。
- [NVIDIA NeMo Guardrails (GitHub)](https://github.com/NVIDIA-NeMo/Guardrails) — v0.20.0，2026 年 1 月。
- [Huang et al. — Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails](https://arxiv.org/abs/2504.11168) — 跨 guard 系统的 ASR 数字。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — classifier 加运行时的框架。
