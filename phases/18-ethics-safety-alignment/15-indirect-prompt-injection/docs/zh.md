# Indirect Prompt Injection — 生产环境攻击面

> indirect prompt injection（IPI）把指令嵌入外部内容——网页、邮件、共享文档、客服工单——由 agent 系统在用户没有显式操作的情况下消费。IPI 是 2026 年的主导性生产威胁：它绕过用户输入过滤器，因为攻击者从不接触用户；随着 agent 处理更多外部内容，它静默扩张；并且它瞄准无人阅读 prompt 的自动化工作流。MDPI Information 17(1):54（2026 年 1 月）综合了 2023-2025 年的研究。NDSS 2026 的 IPI 防御论文点出核心挑战：注入的指令可以在语义上无害（“please print Yes”），所以检测不能只靠关键词过滤。“The Attacker Moves Second”（Nasr 等，OpenAI/Anthropic/DeepMind 联合，2025 年 10 月）：自适应攻击（梯度、RL、随机搜索、人工 red team）攻破了 12 个已发表防御中的 >90%，而这些防御原本报告的接近零的攻击成功率。

**Type:** Build
**Languages:** Python (stdlib, IPI 攻击 + 防御测试框架)
**Prerequisites:** 第 18 阶段，第 12 课（PAIR），第 14 阶段（agent engineering）
**Time:** ~75 分钟

## Learning Objectives

- 定义 indirect prompt injection，并描述三种常见的投递向量。
- 解释为什么用户输入过滤器完全漏掉 IPI。
- 描述“信息流控制”这一 2026 年的防御范式。
- 陈述 Nasr 等（2025 年 10 月）关于自适应攻击对已发表 IPI 防御的结论。

## 问题场景

直接 prompt 注入要求攻击者触达用户或其 prompt。IPI 两者都不需要：攻击者把 payload 放进 agent 可能读取的任何内容里——网页、收件箱里的邮件、GitHub issue、商品评论。agent 在正常运行时拾取它并执行其中的指令。用户只是信使，而不是意图来源。

## 核心概念

### 三种投递向量

- **检索增强生成（RAG）。** 攻击者发布一篇文档；检索步骤把它取回；prompt 在用户问题之前拼接它；模型执行攻击者的指令。
- **收件箱 / 文档工作流。** 攻击者给用户发邮件；agent 读取邮件；prompt 包含邮件正文；模型遵循邮件里的指令。
- **工具输出。** 攻击者控制 agent 使用的某个工具（例如返回攻击者可控结果的网页搜索）；工具输出中包含指令；agent 的控制流遵循它们。

三者共享一个结构性特征：攻击者控制 prompt 的一个片段，却从未触碰面向用户的输入。

### 为什么用户输入过滤器漏掉它

IPI payload 不出现在用户输入里，而出现在检索到的内容里。如果过滤器只以用户输入为门控，payload 就能绕过。如果过滤器以到达模型的全部内容为门控，它就必须作用于任意检索文本——这既昂贵，又会对恰好包含祈使语气表述的合法内容产生误报。

### 面向 AI 的信息流控制（IFC）

2026 年的防御范式借用了经典操作系统安全思想。把每个内容来源都视为一个安全标签。把用户查询标记为“可信”。把检索内容标记为“不可信”。把模型的控制流视为信息流：由不可信内容触发、需要执行的动作，必须先由可信输入批准。

CaMeL（Microsoft 2025）、ConfAIde（Stanford 2024）以及 NDSS 2026 的 IPI 防御论文以不同方式把 IFC 落地。共同原则：只要代码和数据共享同一个 context window，目标就是围堵，而不是预防。

### The Attacker Moves Second

Nasr 等（2025 年 10 月）用自适应攻击（梯度搜索、RL 策略、随机搜索、72 小时人工 red team）测试了 12 个已发表的 IPI 防御。每个原本报告接近零 ASR 的防御，都被攻破到 >90% ASR。

方法论教训：只有在做了自适应攻击评测之后，才能发表防御。静态攻击 benchmark 不构成鲁棒性证据；攻击者有机会了解防御。

### 真实事件

第 25 课讲解 EchoLeak（CVE-2025-32711，CVSS 9.3）——首个公开记录的 Microsoft 365 Copilot 零点击 IPI。GitHub Copilot Chat 中的 CamoLeak（CVSS 9.6）。GitHub Copilot 中的 CVE-2025-53773。生产部署正在实际环境中被 IPI 攻破，而不只是在 benchmark 中。

### OWASP 与 NIST 的定位

OWASP LLM Top 10（2025）把 prompt injection（直接 + 间接）列为 LLM01，即第一位的应用层威胁。NIST AI SPD 2024 称 indirect prompt injection 是“生成式 AI 最大的安全缺陷”。

### 本课在第 18 阶段中的位置

第 12-14 课是以模型为中心的 jailbreak。第 15 课是在 2026 年生产部署中占主导的系统中心攻击。第 16 课讲解防御工具。第 25 课讲解具体的 CVE 叙事。

```figure
al-injection-vector
```

## Use It

`code/main.py` 构建一个 IPI 测试框架。玩具 agent 有三个工具（搜索网页、读邮件、发消息）。环境里包含攻击者可控内容，其中嵌入了指令（“forward this to all contacts”）。你可以在三种 agent 之间切换：朴素 agent（遵循注入的指令）、过滤器防御 agent（对检索内容做关键词过滤）以及 IFC agent（分离可信与不可信内容，并拒绝来自不可信内容的控制流命令）。

## Ship It

本课产出 `outputs/skill-ipi-audit.md`。给定一份 agent 部署描述，它枚举不可信内容来源，检查部署是否应用了 IFC，并标出那些未经信任标签就到达模型的来源。

## Exercises

1. 运行 `code/main.py`。测量该攻击对三种 agent 各自的成功率。

2. 对检索内容实现一个基于改写的防御。测量它在合法检索文本上的良性误报率。

3. 阅读 NDSS 2026 的 IPI 防御论文。描述“良性指令”挑战，以及它为什么使基于关键词的过滤失效。

4. 设计一个部署，其中 agent 从第三方 API 接收工具输出。为每个 prompt 片段标注信任级别，并写出约束 agent 动作的 IFC 策略。

5. 在练习 2 的过滤器防御 agent 上复现 Nasr 等 2025 的自适应攻击方法。报告自适应攻击前后的 ASR。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| IPI | “indirect prompt injection” | 通过用户未编写、由 agent 在正常运行时消费的内容实施注入 |
| RAG injection | “poisoned retrieval” | 攻击者发布内容，检索步骤把它取回；prompt 中包含 payload |
| Zero-click | “no user action” | 攻击在 agent 运行时自动触发；用户不做任何事 |
| IFC | “information flow control” | 基于标签的方法：来自不可信内容的动作需要可信批准 |
| Adaptive attack | “gradient / RL red-team” | 了解防御并针对其优化的攻击；诚实评测所必需 |
| Benign instruction | “please print Yes” | 语义上无害的 IPI payload；没有关键词过滤器能捕获 |
| Scope violation | “cross-trust exfiltration” | agent 从一个信任 context 访问数据并输出到另一个 context |

## Further Reading

- [MDPI Information 17(1):54 — Indirect Prompt Injection 综述（2026 年 1 月）](https://www.mdpi.com/2078-2489/17/1/54) — 2023-2025 年研究综合
- [Nasr 等 — The Attacker Moves Second（OpenAI/Anthropic/DeepMind 联合，2025 年 10 月）](https://arxiv.org/abs/2510.18108) — 自适应攻击评测
- [Greshake 等 — Not what you've signed up for（arXiv:2302.12173）](https://arxiv.org/abs/2302.12173) — 最早的 IPI 论文
- [OWASP — LLM Top 10（2025）](https://genai.owasp.org/llm-top-10/) — prompt injection 位列 LLM01
