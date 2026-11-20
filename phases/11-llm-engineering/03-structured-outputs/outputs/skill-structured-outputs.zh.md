---
name: skill-structured-outputs
description: 根据 provider、可靠性要求和复杂度，选择合适结构化输出策略的决策框架
version: 1.0.0
phase: 11
lesson: 03
tags: [structured-output, json, schema, constrained-decoding, pydantic, function-calling]
---

# 结构化输出策略

构建需要结构化数据的 LLM 应用时，套用这套决策框架。

## 各方案的适用场景

**Prompt 方式（"返回 JSON"）：** 仅用于原型验证。对于偶尔解析失败可容忍的内部工具可以接受。加上带重试的 try/except。绝不要用于生产流水线。

**JSON mode（API 开关）：** 你需要保证 JSON 合法，但 schema 简单或灵活。当你在应用侧校验形状时适用。可用：OpenAI、Anthropic（通过 tool use）、Google。

**Schema mode（constrained decoding）：** 每个输出都必须匹配特定 schema 的生产系统。零解析失败。零 schema 违规。任何生产抽取或分类任务都默认用它。可用：OpenAI structured outputs、Outlines、Guidance。

**Function calling / tool use：** 模型需要选择调用哪个函数，而不仅仅是填参数。你有多个 schema，由模型来选择合适的那一个。与已有工具/函数基础设施集成时也用它。

**Instructor 库：** 你想要 Pydantic 校验，并在任意 provider 上自动重试。对 Python 项目是最佳 DX。封装 OpenAI、Anthropic、Google 及开源模型。

## Provider 特定指引

**OpenAI：** 使用 `response_format` 搭配 `json_schema` 类型。constrained decoding 内置。Pydantic 模型可直接使用。是最可靠的结构化输出实现。

**Anthropic：** 用 tool use 实现结构化输出。定义一个承载目标 schema 的单一 tool。模型返回与 schema 匹配的 tool call 参数。可靠，但需要采用 tool use API 模式。

**开源模型（vLLM、Ollama）：** 用 Outlines 或 Guidance 做 constrained decoding。这些库把 JSON Schema 编译成有限状态机，在生成时屏蔽非法 token。需要在本地运行推理。

## Schema 设计准则

1. 能扁平就保持扁平。嵌套超过 2 层会增加抽取错误。
2. 分类字段用 enum。不要指望模型自己编出正确的字符串。
3. 把有歧义的字段设为必填并显式支持 null，而不是设为可选。这迫使模型做出决定。
4. 给 schema 属性加 description。模型会把这些当作指令来读。
5. 非必要不用联合类型（oneOf/anyOf）。它们会增加解码复杂度。
6. 给数值设置 minimum/maximum。能捕获幻觉出的极端值。
7. 数组上用 minItems/maxItems 防止空输出或无界输出。

## 常见失败模式及修复

- **模型把 JSON 包进 markdown 围栏**：从 prompt 方式切到 JSON mode 或 schema mode
- **schema 合法但事实错误**：在抽取后加一个 LLM-as-judge 校验步骤
- **enum 取值不一致**：改用 constrained decoding，或加后处理归一化
- **缺少可选字段**：把它们设为必填，或在应用代码里加默认值
- **抽取非常慢**：constrained decoding 会增加 5-15% 延迟，对延迟敏感的场合要降低 schema 复杂度
- **元素多样的大数组**：切分输入，逐块抽取，再合并结果

## 可靠性阶梯

| 方案 | 解析成功率 | schema 匹配 | 搭建成本 |
|----------|-------------|-------------|-------------|
| Prompt 方式 | ~90% | ~80% | 1 分钟 |
| JSON mode | 100% | ~90% | 5 分钟 |
| Schema mode | 100% | ~99% | 15 分钟 |
| Constrained decoding | 100% | 100% | 30 分钟 |
| Instructor + 重试 | 100% | ~99.5% | 10 分钟 |
