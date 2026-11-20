# Structured Output —— JSON Schema、Pydantic、Zod、Constrained Decoding

> “好好请模型返回 JSON” 即便在 frontier 模型上也有 5% 到 15% 的失败率。Structured output 通过 constrained decoding 弥补这一差距：模型被字面地禁止产出会违反 schema 的 token。OpenAI 的 strict 模式、Anthropic 的 schema 类型化 tool use、Gemini 的 `responseSchema`、Pydantic AI 的 `output_type`，以及 Zod 的 `.parse`，是同一想法的五种表层形态。本节构建学习者将在每条生产抽取流水线中使用的 schema 校验器与 strict 模式契约。

**Type:** Build
**Languages:** Python（标准库，JSON Schema 2020-12 子集）
**Prerequisites:** 第 13 阶段，第 02 课（function calling 深入剖析）
**Time:** ~75 分钟

## Learning Objectives

- 为抽取目标编写 JSON Schema 2020-12，并使用正确的约束（enum、min/max、required、pattern）。
- 解释为什么 strict 模式与 constrained decoding 提供的保证不同于“生成后再校验”。
- 区分三种失败模式：解析错误、schema 违规、模型拒绝。
- 交付一条带类型化修复与类型化拒绝处理的抽取流水线。

## 问题场景

一个读取采购订单邮件的 agent 需要把自由文本变成 `{customer, line_items, total_usd}`。有三种做法。

**做法一：用 prompt 要求 JSON。** “用 JSON 回复，字段为 customer、line_items、total_usd。” 在 frontier 模型上 85% 到 95% 的情况有效。它会在六个方面失败：缺少花括号、多余逗号、类型错误、幻觉字段、在 token 上限处截断、泄漏散文式的 “Here is your JSON:”。

**做法二：生成后校验。** 自由生成、解析、按 schema 校验，失败则重试。可靠但昂贵——每次重试都要付费，而截断类 bug 每发生一次就多付一轮。

**做法三：constrained decoding。** provider 在解码时强制执行 schema。非法的 token 被从采样分布中屏蔽。输出保证可解析、保证通过校验。失败塌缩成一种模式：拒绝（模型判定输入不符合 schema）。

2026 年的每个 frontier provider 都提供某种形式的做法三。

- **OpenAI。** `response_format: {type: "json_schema", strict: true}`，若模型拒绝，响应中会带 `refusal`。
- **Anthropic。** 对 `tool_use` 输入做 schema 强制；`stop_reason: "refusal"` 并不存在，信号是只以 `end_turn` 结束且没有工具调用。
- **Gemini。** 请求级的 `responseSchema`；2026 年 Gemini 针对选定的类型提供 token 级语法约束。
- **Pydantic AI。** `output_type=InvoiceModel` 产出一个类型化为 `InvoiceModel` 的结构化 `RunResult`。
- **Zod（TypeScript）。** 一个运行时解析器，按 Zod schema 校验 provider 输出；与 OpenAI 的 `beta.chat.completions.parse` 配合使用。

共同的主线：只声明一次 schema，端到端地强制执行它。

## 核心概念

### JSON Schema 2020-12 —— 通用语

每家 provider 都接受 JSON Schema 2020-12。最常用的构造：

- `type`：取 `object`、`array`、`string`、`number`、`integer`、`boolean`、`null` 之一。
- `properties`：字段名到子 schema 的映射。
- `required`：必须出现的字段名清单。
- `enum`：允许取值的封闭集合。
- `minimum` / `maximum`（数字），`minLength` / `maxLength` / `pattern`（字符串）。
- `items`：作用于每个数组元素的子 schema。
- `additionalProperties`：设为 `false` 时禁止额外字段（默认值因模式而异）。

OpenAI strict 模式额外提出三条要求：每个属性都必须列在 `required` 中，所有地方都要 `additionalProperties: false`，且不允许未解析的 `$ref`。违反这些要求时，API 会在请求阶段返回 400。

### Pydantic，Python 绑定

Pydantic v2 通过 `model_json_schema()` 从 dataclass 形状的模型生成 JSON Schema。Pydantic AI 对其做了封装，于是你写：

```python
class Invoice(BaseModel):
    customer: str
    line_items: list[LineItem]
    total_usd: Decimal
```

agent 框架会在边缘处把 schema 转换成 OpenAI strict 模式、Anthropic 的 `input_schema` 或 Gemini 的 `responseSchema`。模型的输出以类型化的 `Invoice` 实例返回。校验失败会抛出 `ValidationError`，带有类型化的错误路径。

### Zod，TypeScript 绑定

Zod（`z.object({customer: z.string(), ...})`）是 TypeScript 的等价物。OpenAI 的 Node SDK 暴露 `zodResponseFormat(Invoice)`，它会被转换成 API 的 JSON Schema 载荷。

### 拒绝

strict 模式无法强迫模型作答。如果输入无法符合 schema（“这封邮件是一首诗，不是发票”），模型会产出一个包含原因的 `refusal` 字段。你的代码必须把它当作一等结果来处理，而不是失败。拒绝同时也是有用的安全信号：当一个模型被要求从受保护内容的邮件中抽取信用卡号时，它会返回一个附带了安全原因的拒绝。

### 开放实现中的 constrained decoding

开放权重实现使用三种技术。

1. **基于语法的解码**（`outlines`、`guidance`、`lm-format-enforcer`）：从 schema 构建确定性有限自动机；每一步屏蔽掉会违反该 FSM 的 token 的 logits。
2. **配合 JSON 解析器的 logit 屏蔽**：与模型同步运行一个流式 JSON 解析器；每一步计算合法的下一 token 集合。
3. **带验证器的投机解码**：由廉价的草稿模型提议 token，验证器强制执行 schema。

商业 provider 在后台选择其中一种。2026 年的技术现状是：对短的结构化输出，它比普通生成更快；对长输出则大致相当。

### 三种失败模式

1. **解析错误。** 输出不是合法 JSON。在 strict 模式下不可能发生。在非 strict 的 provider 上仍可能发生。
2. **schema 违规。** 输出可以解析，但违反 schema。在 strict 模式下不可能发生。在其之外很常见。
3. **拒绝。** 模型拒绝作答。必须作为类型化结果处理。

### 重试策略

当你处于 strict 模式之外（Anthropic 的 tool use、非 strict 的 OpenAI、较旧的 Gemini）时，恢复模式是：

```
generate -> parse -> validate -> if fail, inject error and retry, max 3x
```

通常一次重试就够了。三次重试可以兜住弱模型的偶发故障。超过三次说明 schema 有问题：模型对某些输入无法满足它，prompt 或 schema 需要修改。

### 小模型支持

constrained decoding 在小模型上同样有效。一个带语法强制、30 亿参数的开源模型，在结构化任务上胜过 700 亿参数、只用原生 prompt 的模型。这正是 structured output 对生产至关重要的主因：它把可靠性与模型规模解耦。

```figure
constrained-decoding
```

## Use It

`code/main.py` 用标准库交付一个极简的 JSON Schema 2020-12 校验器（types、required、enum、min/max、pattern、items、additionalProperties）。它包裹一个 `Invoice` schema，并把一段假的 LLM 输出送进校验器，演示解析错误、schema 违规与拒绝三条路径。在生产中把假输出换成任意 provider 的真实响应即可。

值得关注的点：

- 校验器返回一份类型化的 `[ValidationError]` 列表，带路径与消息。这正是你希望暴露给重试 prompt 的形态。
- 拒绝分支**不会**重试。它记录日志并返回一个类型化的拒绝。Phase 14 · 09 把拒绝用作安全信号。
- `additionalProperties: false` 检查会在对抗性测试输入上触发，说明为什么 strict 模式堵死了幻觉字段的门。

## Ship It

本节产出 `outputs/skill-structured-output-designer.md`。给定一个自由文本抽取目标（发票、工单、简历等），该 skill 产出一份兼容 strict 模式的 JSON Schema 2020-12，以及一份与之对应的 Pydantic 模型，并预置类型化的拒绝与重试处理。

## Exercises

1. 运行 `code/main.py`。添加第四个测试用例，其 `total_usd` 为负数。确认校验器以 `minimum` 约束路径拒绝它。

2. 扩展校验器以支持带判别器的 `oneOf`。常见场景：`line_item` 要么是产品要么是服务，由 `kind` 标记。strict 模式在这里有微妙的规则；查阅 OpenAI 的 structured outputs 指南。

3. 用 Pydantic BaseModel 编写同样的 Invoice schema，把 `model_json_schema()` 的输出与手写的 schema 做比较。找出 Pydantic 默认设置、而手写版本遗漏的那个字段。

4. 测量拒绝率。构造十个本不应被抽取的输入（一段歌词、一个数学证明、一封空白邮件），用 strict 模式的真实 provider 跑一遍。统计拒绝与幻觉输出的数量。这是你面向拒绝感知重试的真值基准。

5. 从头到尾读一遍 OpenAI 的 structured outputs 指南。找出它在 strict 模式下明确禁止、而普通 JSON Schema 允许的那一个构造。然后设计一个非必要地使用该构造的 schema，并把它重构为 strict 兼容。

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------------|------------------------|
| JSON Schema 2020-12 | “schema 规范” | 每个现代 provider 都使用的 IETF 草案 schema 方言 |
| Strict mode | “保证 schema” | OpenAI 的标志，通过 constrained decoding 强制执行 schema |
| Constrained decoding | “logit 屏蔽” | 解码时强制，屏蔽非法的下一 token |
| Refusal | “模型拒绝” | 输入无法符合 schema 时的类型化结果 |
| Parse error | “非法 JSON” | 输出无法按 JSON 解析；strict 下不可能 |
| Schema violation | “形状不对” | 可解析但违反 types / required / enum / range |
| `additionalProperties: false` | “不许有额外字段” | 禁止未知字段；OpenAI strict 中强制要求 |
| Pydantic BaseModel | “类型化输出” | 产出并校验 JSON Schema 的 Python 类 |
| Zod schema | “TypeScript 输出类型” | 用于校验 provider 输出的 TS 运行时 schema |
| Grammar enforcement | “开放权重 constrained decode” | 基于 FSM 的 logit 屏蔽，如 outlines / guidance |

## Further Reading

- [OpenAI — Structured outputs](https://platform.openai.com/docs/guides/structured-outputs) — strict 模式、拒绝与 schema 要求
- [OpenAI — Introducing structured outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/) — 2024 年 8 月的发布文章，解释解码保证
- [Pydantic AI — Output](https://ai.pydantic.dev/output/) — 类型化的 output_type 绑定，可序列化到各家 provider
- [JSON Schema — 2020-12 release notes](https://json-schema.org/draft/2020-12/release-notes) — 规范原文
- [Microsoft — Structured outputs in Azure OpenAI](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs) — 企业部署说明与 strict 模式注意事项
