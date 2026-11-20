# ASCII Art and Visual Jailbreaks

> Jiang、Xu、Niu、Xiang、Ramasubramanian、Li、Poovendran，“ArtPrompt: ASCII Art-based Jailbreak Attacks against Aligned LLMs”（ACL 2024, arXiv:2402.11753）。把有害请求中与安全相关的 token 掩码，替换成同一字母的 ASCII art 渲染，然后发送这层伪装后的 prompt。GPT-3.5、GPT-4、Gemini、Claude、Llama-2 都无法稳健地识别 ASCII art token。该攻击绕过了 PPL（perplexity 过滤器）、Paraphrase 防御与 Retokenization。相关工作：ViTC benchmark 衡量对非语义视觉 prompt 的识别能力；StructuralSleight 把攻击推广到 Uncommon Text-Encoded Structures（树、图、嵌套 JSON）这一编码攻击族别。

**Type:** Build
**Languages:** Python (stdlib, ArtPrompt token 掩码测试框架)
**Prerequisites:** 第 18 阶段，第 12 课（PAIR）、第 13 课（MSJ）
**Time:** ~60 分钟

## Learning Objectives

- 描述 ArtPrompt 攻击：词识别步骤、ASCII art 替换、最终伪装 prompt。
- 解释为什么标准防御（PPL、Paraphrase、Retokenization）在 ArtPrompt 上失效。
- 定义 ViTC 并描述它衡量什么。
- 描述 StructuralSleight 如何推广到任意 Uncommon Text-Encoded Structures。

## 问题场景

通过改写与角色扮演的攻击（第 12 课）和通过长 context 的攻击（第 13 课）作用于文本层面的模式。ArtPrompt 作用于识别层面：模型并不解析被禁止的 token，而是解析一张由字符渲染出的图像。安全过滤器看到的是一堆无害标点。模型看到的是一个词。

## 核心概念

### ArtPrompt 的两个步骤

步骤 1。词识别。给定一个有害请求，攻击者用 LLM 找出与安全相关的词（例如 “how to make a bomb” 中的 “bomb”）。

步骤 2。伪装 prompt 生成。把每个识别出的词替换成它的 ASCII art 渲染（由字符组成 7x5 或 7x7 的区块，构成字母形状）。模型收到的是一片由标点与空格组成的网格，能力足够的模型能把它识别为词；而安全过滤器只看到网格。

结果：GPT-4、Gemini、Claude、Llama-2、GPT-3.5 全部失效。在其 benchmark 子集上攻击成功率超过 75%。

### 为什么标准防御会失效

- **PPL（perplexity 过滤器）。** ASCII art 的 perplexity 很高——但所有新颖输入都是如此。能拦住 ArtPrompt 的阈值选择，同样会拦住合法的结构化输入。
- **Paraphrase。** 改写 prompt 会破坏 ASCII art。但在实践中，改写型 LLM 往往会保留甚至重建这些图案。
- **Retokenization。** 用不同方式切分 token，并不能改变模型是在靠“视觉”识别字母形状这一事实。

底层问题在于：安全过滤器是 token 级或语义级的；而 ArtPrompt 作用于视觉识别层面。

### ViTC benchmark

衡量对非语义视觉 prompt 的识别能力。测量模型读取 ASCII art、wingdings 以及其他非文本语义视觉内容的能力。ArtPrompt 的有效性与 ViTC 准确率相关：模型读视觉文本越强，ArtPrompt 对它越有效。这是一种能力-安全权衡。

### StructuralSleight

推广了 ArtPrompt：Uncommon Text-Encoded Structures（UTES）。树、图、嵌套 JSON、JSON 中的 CSV、diff 风格代码块。如果某种结构在训练安全数据中很少见，但模型又能解析，它就可以用来隐藏有害内容。

防御的含义：安全必须泛化到模型可解析的各种结构化表示。这个集合很大，而且在不断增长。

### 图像模态的类比

视觉 LLM（GPT-5.2、Gemini 3 Pro、Claude Opus 4.5、Grok 4.1）扩展了攻击面。用真实图像实施的 ArtPrompt 式攻击比 ASCII art 版本更强，因为图像编码器产出的信号更丰富。

### 本课在第 18 阶段中的位置

第 12-14 课描述了三个正交的攻击向量：迭代精炼（PAIR）、context 长度（MSJ）以及编码（ArtPrompt/StructuralSleight）。第 15 课从以模型为中心的攻击转向系统边界攻击（indirect prompt injection）。第 16 课描述防御工具层的回应。

```figure
al-ascii-cloak
```

## Use It

`code/main.py` 构建一个玩具 ArtPrompt。你可以用 ASCII art 字形把有害查询中的特定词伪装起来，验证伪装后的字符串能通过关键词过滤器，并且（可选地）用简单的识别器把伪装字符串解码回来。

## Ship It

本课产出 `outputs/skill-encoding-audit.md`。给定一份 jailbreak 防御报告，它枚举所覆盖的编码攻击族别（ASCII art、base64、leet-speak、UTF-8 homoglyph、UTES）以及能捕获每一类的防御层。

## Exercises

1. 运行 `code/main.py`。验证伪装后的字符串能通过一个简单的关键词过滤器。报告所需的字符级改动。

2. 实现第二种编码：对同一个目标词使用 base64。比较它相对 ArtPrompt 的过滤器绕过率，以及两者的恢复难度。

3. 阅读 Jiang 等 2024 第 4.3 节（五个模型的结果）。给出一个理由，解释为什么在同一 benchmark 上 Claude 对 ArtPrompt 的抵抗力高于 Gemini。

4. 设计一个生成前防御，检测 prompt 中呈 ASCII art 形状的区域。测量它在合法代码、表格与数学记号上的误报率。

5. StructuralSleight 列出了 10 种编码结构。勾勒一个能处理全部 10 种的通用防御，并估算每个受防御 prompt 的计算成本。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| ArtPrompt | “the ASCII-art attack” | 用 ASCII art 渲染掩盖安全相关词的两步式 jailbreak |
| Cloaking | “hide the word” | 用模型能读出、过滤器读不出的视觉表示替换被禁止的 token |
| UTES | “uncommon structure” | Uncommon Text-Encoded Structure——树、图、嵌套 JSON 等，用于夹带内容 |
| ViTC | “visual-text capability” | 衡量模型读取非语义视觉编码能力的 benchmark |
| Perplexity filter | “PPL defense” | 拒绝高 perplexity 的 prompt；失效是因为合法的结构化输入得分同样高 |
| Retokenization | “tokenizer shift defense” | 用不同 tokenizer 预处理 prompt；失效是因为识别发生在视觉层面 |
| Homoglyph | “lookalike characters” | 与拉丁字母看起来相同的 Unicode 字符；可绕过子串检查 |

## Further Reading

- [Jiang 等 — ArtPrompt（ACL 2024, arXiv:2402.11753）](https://arxiv.org/abs/2402.11753) — ASCII art jailbreak 论文
- [Li 等 — StructuralSleight（arXiv:2406.08754）](https://arxiv.org/abs/2406.08754) — UTES 推广
- [Chao 等 — PAIR（第 12 课，arXiv:2310.08419）](https://arxiv.org/abs/2310.08419) — 互补的迭代攻击
- [Anil 等 — Many-shot Jailbreaking（第 13 课）](https://www.anthropic.com/research/many-shot-jailbreaking) — 互补的长度攻击
