# 工具使用与 Function Calling

> Toolformer（Schick 等人，2023）开创了自监督的工具标注。Berkeley Function Calling Leaderboard V4（Patil 等人，2025）设定了 2026 年的标准：40% agentic、30% multi-turn、10% live、10% non-live、10% hallucination。单轮已经解决。记忆、动态决策和长时程工具链还没有。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 13 · 01 (Function Calling Deep Dive)
**Time:** ~60 minutes

## 学习目标

- 解释 Toolformer 的自监督训练信号：只有当执行工具能降低下一个 token 的 loss 时才保留工具标注。
- 说出 BFCL V4 的五个评估类别，以及每个衡量什么。
- 用标准库实现一个带 schema 验证、参数强制转换和执行沙箱的工具注册表。
- 诊断三个 2026 年的开放问题：长时程工具链、动态决策和记忆。

## 问题

早期的工具使用问的是：模型能预测一个正确的函数调用吗？现代的工具使用问的是：模型能否跨 40 步链接工具，带记忆、带部分可观测性、能从工具失败中恢复，而不幻觉出不存在的工具？

Toolformer 建立了基线：模型可以通过自监督学会何时调用工具。BFCL V4 定义了 2026 年的评估目标。两者之间的差距，就是生产智能体生存的空间。

## 概念

### Toolformer（Schick 等人，NeurIPS 2023）

思路：让模型用自己的预训练语料标注候选 API 调用。对每个候选，执行它。只有当包含工具结果能降低下一个 token 的 loss 时，才保留该标注。在过滤后的语料上微调。

覆盖的工具：计算器、QA 系统、搜索引擎、翻译器、日历。自监督信号纯粹关于「工具是否有助于预测文本」——没有人工标签。

规模结果：工具使用在规模上涌现。较小的模型会因工具标注而受损；较大的模型获益。这就是为什么 2026 年的前沿模型天生就有很强的工具使用，而大多数 7B 模型需要显式的工具使用微调才能可靠。

### Berkeley Function Calling Leaderboard V4（Patil 等人，ICML 2025）

BFCL 是 2026 年事实上的评估。V4 构成：

- **Agentic（40%）** —— 完整智能体轨迹：记忆、多轮、动态决策。
- **Multi-Turn（30%）** —— 带工具链的交互式对话。
- **Live（10%）** —— 用户提交的真实提示词（更难的分布）。
- **Non-Live（10%）** —— 合成测试用例。
- **Hallucination（10%）** —— 检测何时不应调用工具。

V3 引入了基于状态的评估：在一段工具序列之后，检查 API 的实际状态（例如「文件创建了吗？」），而不是匹配工具调用的 AST。V4 增加了 web search、memory 和格式敏感性类别。

2026 年的关键发现：单轮 function calling 已接近解决。失败集中在记忆（跨轮携带上下文）、动态决策（根据先前结果选择工具）、长时程链（20+ 步之后漂移）和幻觉检测（在没有工具适用时拒绝调用）。

### 工具 schema

每个 provider 都有自己的 schema。细节各异，但形状相同：

```
name: string
description: string (what it does, when to use it)
input_schema: JSON Schema (properties, required, types, enums)
```

Anthropic 直接用 `input_schema`。OpenAI 用 `function.parameters`。两者都接受 JSON Schema。描述是承重的——模型靠读它来挑对工具。糟糕的工具描述是「选错工具」失败的第一大根因。

### 参数验证

不要相信任何工具调用。验证：

1. **类型强制转换。** 模型可能返回字符串 "5"，而 schema 说是 int。无歧义则强制转换；有歧义则拒绝。
2. **枚举验证。** 如果 schema 说 `status in {"open", "closed"}`，而模型输出 `"in_progress"`，用描述性错误拒绝。
3. **必填字段。** 缺失必填字段 -> 立即把错误观察回喂给模型，而不是崩溃。
4. **格式验证。** 日期、邮箱、URL——用具体解析器验证，而不是正则。

每一次验证失败都应当返回一条结构化观察，让模型能以正确形状重试。

### 并行工具调用

现代 provider 支持在一个 assistant 回合里并行工具调用。循环：

1. 模型发出 3 个带不同 `tool_use_id` 的工具调用。
2. 运行时执行它们（相互独立则并行）。
3. 每个结果以按 `tool_use_id` 关联的 `tool_result` 块返回。

工程规则：把关联 ID 当作承重对象。交换它们，你就会把错误的工具路由到错误的结果。

### 沙箱

工具执行是沙箱边界。详见第 09 课。短版本：每个工具都应指定读/写面、网络访问、超时、内存上限。泛化的 `run_shell(cmd)` 是红旗；具体的 `git_status()` 更安全。

```figure
tool-routing
```

## Build It

`code/main.py` 实现了一个生产形态的工具注册表：

- JSON Schema 子集验证器（仅标准库）。
- 带描述、输入 schema、超时和执行器的工具注册。
- 参数强制转换和枚举验证。
- 带关联 ID 的并行工具派发。
- 作为结构化字符串的错误观察。

运行它：

```
python3 code/main.py
```

trace 展示一个迷你智能体在一个回合里调用三个工具，其中有一个故意格式错误的调用，被以模型可以据此行动的描述性错误拒绝。

## Use It

每个 provider 都有自己的工具 schema——Anthropic、OpenAI、Gemini、Bedrock。如果你需要多 provider，用一个转换层（OpenAI Agents SDK、Vercel AI SDK、LangChain tool adapter）。如果工具使用是产品的核心，在上线前用 BFCL（参考基准）跑你的智能体。

## Ship It

`outputs/skill-tool-registry.md` 为一个给定任务领域生成工具目录、schema 和注册表。包含描述质量检查（每个工具的描述是否告诉模型何时使用它？）。

## 练习

1. 加一个「no-op」工具，让模型可以显式拒绝使用任何其他工具。在类 BFCL 的幻觉测试上测量。
2. 实现 int-as-string 和 float-as-string 的参数强制转换。强制转换在哪里开始掩盖真正的 bug？
3. 加一个每工具超时和一个熔断器（连续 3 次失败后 60 秒内拒绝该工具）。这如何改变模型的恢复方式？
4. 读 BFCL V4 描述。挑一个类别（例如「multi-turn」）并通过你的智能体跑 10 个示例提示词。报告通过率。
5. 把标准库验证器移植到 Pydantic 或 Zod。Pydantic/Zod 抓住了什么玩具版漏掉的？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------|------------------|
| Function calling | 「工具使用」 | 带已验证 schema 的结构化输出工具调用 |
| Toolformer | 「自监督工具标注」 | Schick 2023——只保留其结果能降低下一个 token loss 的工具调用 |
| BFCL | 「Berkeley Function Calling Leaderboard」 | 2026 基准：40% agentic、30% multi-turn、10% live、10% non-live、10% hallucination |
| Tool schema | 「给模型的函数签名」 | name、description、参数的 JSON Schema |
| tool_use_id | 「关联 ID」 | 把工具调用与其结果绑定；对并行派发必不可少 |
| Hallucination detection | 「知道何时不调用」 | V4 类别：在没有工具适用时拒绝调用 |
| Argument coercion | 「字符串到 int 的修复」 | 针对可预测 schema 不匹配的窄修复；有歧义则拒绝 |
| Sandboxing | 「工具执行边界」 | 每工具的读/写面、网络、超时、内存上限 |

## 延伸阅读

- [Schick 等人，Toolformer（arXiv:2302.04761）](https://arxiv.org/abs/2302.04761)——自监督工具标注
- [Berkeley Function Calling Leaderboard (V4)](https://gorilla.cs.berkeley.edu/leaderboard.html)——2026 评估基准
- [Anthropic，Tool use documentation](https://platform.claude.com/docs/en/agent-sdk/overview)——Claude Agent SDK 中的生产工具 schema
- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/)——function tool 类型与 Guardrails
