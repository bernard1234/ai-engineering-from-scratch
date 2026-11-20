---
name: skill-function-calling-patterns
description: 在生产环境实现 function calling 的决策框架 —— tool 设计、错误处理、安全和各 provider 的模式
version: 1.0.0
phase: 11
lesson: 09
tags: [function-calling, tool-use, agents, mcp, security, openai, anthropic]
---

# Function Calling 模式

在构建使用 tool 的 LLM 应用时，套用这套决策框架。

## 何时使用 function calling

**在以下情况使用 function calling：**
- 模型需要实时数据（天气、股价、数据库查询）
- 任务需要副作用（发邮件、创建记录、部署代码）
- 模型必须根据用户意图在多个动作之间做选择
- 你在构建与外部系统交互的 agent

**在以下情况改用 structured outputs：**
- 你需要从文本中抽取数据（不需要外部调用）
- 输出本身就是最终产物，而不是中间步骤
- 你只有一个 schema，不需要在多个 tool 之间做选择

**在以下情况两者都用：**
- 模型先调用 tool，再把 tool 结果组织成特定的输出格式

## Tool 设计准则

1. **一个 tool 只做一件事。** 一个名为 `manage_database`、同时处理查询、插入、更新和删除的 tool 太宽泛。拆成 `query_records`、`insert_record`、`update_record`。模型在具体的 tool 面前选择得更好。

2. **Description 就是 prompt。** 模型通过读 tool description 来决定选哪个。写 description 就像给初级开发者写说明。要写明 tool 返回什么，而不只是做什么。

3. **用 enum 约束。** 如果一个参数只有 3-10 个合法取值，就用 enum。除非你加以约束，模型会自己发明字符串 —— "celsius"、"Celsius"、"C"、"metric"。

4. **tool 越少越好。** GPT-4o 能很好地处理 5-10 个 tool。到 20+ 个 tool 时，选择准确率开始下降。到 50+ 个 tool 时，预期会有 10-15% 的选错率。把相关功能分组，或加一层 routing。

5. **required 就是必须。** 只有当 tool 少了这个参数就完全无法工作时，才把它标为 required。带合理默认值的可选参数能减少 tool 调用失败。

## 各 provider 的模式

### OpenAI（GPT-4o、o3、GPT-4o-mini）

```python
tools=[{"type": "function", "function": {"name": ..., "parameters": ...}}]
tool_choice="auto"       # model decides
tool_choice="required"   # must call at least one tool
tool_choice={"type": "function", "function": {"name": "specific_tool"}}
```

- 支持并行 tool 调用（一次响应中出现多个 `tool_calls`）
- tool call ID 必须随结果一起回传
- `gpt-4o-mini` 便宜 10 倍，处理简单的 tool 路由效果很好
- structured outputs 模式可以与 tool 参数一起用，保证符合 schema

### Anthropic（Claude 3.5 Sonnet、Claude 4 Opus）

```python
tools=[{"name": ..., "description": ..., "input_schema": ...}]
tool_choice={"type": "auto"}     # model decides
tool_choice={"type": "any"}      # must call at least one tool
tool_choice={"type": "tool", "name": "specific_tool"}
```

- tool 调用以 `type: "tool_use"` 的 content block 形式出现
- 结果放在 `type: "tool_result"` 的 user 消息里
- 字段名是 `input_schema`，不是 `parameters`（迁移时常见的 bug）
- 支持一次响应中多次 tool 调用

### Google（Gemini 2.0 Flash、Gemini 2.0 Pro）

```python
function_declarations=[{"name": ..., "description": ..., "parameters": ...}]
function_calling_config={"mode": "AUTO"}   # or "ANY" or "NONE"
```

- 在顶层使用 `function_declarations`
- 结果通过 `function_response` part 返回
- 支持并行 function calling

### 开源模型（Llama 3、Hermes、Qwen）

- 没有统一格式 —— 因模型和 serving 框架而异
- Hermes 格式（NousResearch）是最常见的微调约定
- vLLM 对受支持的模型提供 OpenAI 兼容的 tool calling
- Ollama 对兼容模型提供基础的 tool calling
- 上线前先测 tool 选择准确率 —— 在 Berkeley Function Calling Leaderboard 上，开源模型比 GPT-4o 低 15-30%

## 错误处理模式

### 返回结构化错误

```json
{"error": true, "message": "City 'Toky' not found. Did you mean 'Tokyo'?", "code": "NOT_FOUND", "suggestions": ["Tokyo"]}
```

错误信息要包含可操作的信息。"Not found" 很差。"Not found, did you mean X?" 就很好。模型会利用错误信息自我纠正。

### 重试策略

1. tool 调用因可纠正的错误失败（拼写错误、enum 取值错误）
2. 把错误作为 tool 结果发回给模型
3. 模型调整后重试
4. 每次 tool 调用最多重试 3 次
5. 3 次失败后，把错误返回给用户

### 超时处理

为所有 tool 执行设置超时。30 秒是合理的默认值。如果 tool 超时，返回结构化的超时错误，让模型能告知用户，而不是一直挂起。

## 安全检查清单

| 检查项 | 原因 | 做法 |
|-------|-----|-----|
| 函数白名单 | 防止任意代码执行 | 只注册用户需要的 tool |
| 校验参数类型 | 防止类型混淆攻击 | 执行前检查类型 |
| 净化字符串参数 | 防止注入 | 拒绝或转义特殊字符 |
| 参数化数据库查询 | 防止 SQL 注入 | 绝不要直接传入模型生成的 SQL |
| 过滤 tool 结果 | 防止数据泄漏 | 移除 API key、PII、内部错误信息 |
| 限制 tool 调用速率 | 防止失控循环 | 每个对话最多 10-20 次调用 |
| 记录所有 tool 调用 | 审计追踪 | 存储 tool 名、参数、结果、时间戳 |
| 阻断路径穿越 | 防止文件系统访问 | 文件类 tool 中拒绝 `..` 和绝对路径 |
| 沙箱化代码执行 | 防止系统访问 | 使用容器或受限的 builtins |
| 校验返回大小 | 防止上下文填充 | 截断超过 10KB 的结果 |

## 性能优化

- **并行调用：** 当模型请求多个相互独立的 tool 时，用 `asyncio.gather()` 或 `concurrent.futures` 并发执行
- **缓存：** 对同一 session 内参数完全相同的 tool 结果做缓存（天气在 60 秒内不会变）
- **流式输出：** 在获取 tool 结果的同时，流式输出模型的最终响应
- **Tool 精简：** 如果上下文紧张，只放与当前 query 相关的 tool 定义（用一个分类器来筛选）
- **用更小的模型做 routing：** 用 `gpt-4o-mini` 或 `claude-haiku-4-5` 做 tool 选择，再把结果交给更强的模型做综合

## 常见失败模式

| 失败现象 | 原因 | 修复 |
|---------|-------|-----|
| 选错 tool | description 含糊 | 重写 description，加入具体的触发词 |
| 缺少必需参数 | 模型漏了某个参数 | 在参数 description 中加入清晰的示例 |
| tool 无限循环 | 模型反复调用同一个 tool | 设置最大迭代次数（5-10）并检测重复调用 |
| 编造参数 | 模型编出貌似合理但错误的值 | 使用 enum，并对照已知取值做校验 |
| tool 结果过大 | API 返回了 100KB 数据 | 回传前先截断或摘要 |
| 模型忽略 tool 结果 | 结果格式令人困惑 | 返回字段名清晰的干净 JSON |
