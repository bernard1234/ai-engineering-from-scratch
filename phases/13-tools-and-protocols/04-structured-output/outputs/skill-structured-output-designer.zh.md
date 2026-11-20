---
name: structured-output-designer
description: 为自由文本抽取目标设计一份兼容 strict 模式的 JSON Schema 与对应 Pydantic 模型，并预置类型化的拒绝与重试处理。
version: 1.0.0
phase: 13
lesson: 04
tags: [structured-output, json-schema, pydantic, strict-mode, extraction]
---

给定一个自由文本抽取目标（发票、简历、工单、研究摘要），产出一份可直接用于生产的抽取契约：JSON Schema 2020-12、Pydantic 模型、拒绝处理器与重试策略。

产出：

1. JSON Schema 2020-12。每个属性都有类型。`required` 列出所有属性。每个对象都带 `additionalProperties: false`。封闭取值集合使用 Enum。不用 `$ref`。不用模棱两可的 `oneOf` / `anyOf`。按 OpenAI strict 模式的要求校验通过。
2. Pydantic v2 BaseModel。与 schema 对应的 Python 类型镜像。`model_json_schema()` 必须产出与 (1) 等价的 schema。
3. 拒绝处理器。类型化的 `Refusal(reason: str, category: str)` 结果。列出分类：`safety`、`input_mismatch`、`insufficient_info`。
4. 重试策略。三种重试形态：(a) 注入校验错误并重试一次（strict 模式之外）；(b) 把拒绝视为最终结果（strict 模式）；(c) 反复拒绝时升级到更强的模型。
5. 测试向量。十个输入，覆盖正常路径、对抗性字段、部分输入，以及一个触发拒绝的用例。每个都标明预期结果。

硬性拒绝：
- 任何含无类型字段的 schema。既过不了 strict 模式也过不了校验器。
- 任何缺少 `additionalProperties: false` 的 schema。会泄漏幻觉。
- 任何使用 `oneOf` 却没有判别器字段的 schema。解码有歧义。
- 任何尚未核验 JSON Schema 往返一致性的 Pydantic 模型。

拒绝规则：
- 如果目标领域包含个人身份数据却没有记录在案的用途，拒绝并引导至 Phase 18（伦理），先论证合法性基础。
- 如果用户要求一个无法用 JSON Schema 2020-12 表达的 schema（例如任意递归图），拒绝并给出最接近的可表达放宽方案。
- 如果抽取目标被描述为“从任何东西里抽取结构化数据”，拒绝并追问具体领域。

输出：一份单页契约，含 schema JSON、Pydantic 类、拒绝与重试策略，以及十个测试向量。结尾说明首个要针对的 provider 及其原因。
