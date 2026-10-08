# 记忆块与 Sleep-Time Compute

> 离散的功能性记忆块，模型可以直接编辑；以及一个 sleep-time agent，在主 agent 空闲时异步整合记忆。这两个想法是你把记忆扩展到单次对话之外的方法。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 07 (MemGPT)
**Time:** ~75 minutes

## 学习目标

- 说出 Letta 使用的三个记忆层（core、recall、archival）以及各自的角色。
- 解释 memory-block 模式：Human block、Persona block 和用户自定义 block 作为一等有类型对象。
- 描述 sleep-time compute 是什么、为什么它在关键路径之外，以及为什么它能运行比主 agent 更强的模型。
- 实现一个脚本化的双 agent 循环：主 agent 提供响应，sleep-time agent 在轮次之间整合 blocks。

## 问题

MemGPT（Lesson 07）解决了虚拟记忆的控制流。随后出现了三个生产问题：

1. **延迟。** 每个记忆操作都在关键路径上。如果 agent 不得不在用户等待时做裁剪、摘要或对账，尾部延迟会爆炸。
2. **记忆腐烂。** 写入累积。被推翻的事实留在原地。检索淹没在过时内容里。
3. **结构丢失。** 扁平的 archival 存储无法表达「Human block 始终在 prompt 里；Persona block 始终在 prompt 里；Task block 每次会话都换」。

Letta（letta.com）是原 MemGPT 项目 2024 年采用的平台名称——论文里的模式保留 MemGPT 这个名字——而 2026 年的 Letta V1 重写是更晚、独立的一步。Memory blocks 让结构显式化；sleep-time compute 把整合移出关键路径。

## 概念

### 三层

| 层 | 范围 | 住在哪里 | 由谁写入 |
|------|-------|----------------|------------|
| Core | 始终可见 | 主 prompt 内部 | Agent tool call + sleep-time 重写 |
| Recall | 对话历史 | 可检索 | 自动的轮次记录 |
| Archival | 任意事实 | Vector + KV + graph | Agent tool call + sleep-time 摄入 |

Core 就是 MemGPT 的 core。Recall 是对话缓冲区及其被驱逐的尾部。Archival 是外部存储。这个划分清理了 MemGPT 两层的过载。

### Memory blocks

Block 是 core 层中一个带类型、持久、可编辑的 section。原 MemGPT 论文定义了两个：

- **Human block** —— 关于用户的事实（姓名、角色、偏好、目标）。
- **Persona block** —— agent 的自我概念（身份、语气、约束）。

Letta 推广到任意的用户自定义 blocks：当前目标的 `Task` block、代码库事实的 `Project` block、硬约束的 `Safety` block。每个 block 有 `id`、`label`、`value`、`limit`（字符上限）、`description`（让模型知道何时编辑它）。

Blocks 可通过工具表面编辑：

- `block_append(label, text)`
- `block_replace(label, old, new)`
- `block_read(label)`
- `block_summarize(label)` —— 压缩一个接近上限的 block。

### Sleep-time compute

2025 年 Letta 的新增内容：在后台运行第二个 agent，处于关键路径之外。Sleep-time agents 处理对话转录和代码库上下文，把 `learned_context` 写进共享 blocks，并整合或失效 archival 记录。

由此而来的特性：

- **无延迟成本。** 主响应不用等待记忆操作。
- **允许更强的模型。** sleep-time agent 可以用更贵、更慢的模型，因为它不受延迟约束。
- **自然的整合窗口。** 在用户不等待时做去重、摘要、失效被推翻的事实。

形态与人类工作方式一致：你先做任务，睡一觉，长期记忆在一夜之间沉淀。

### Native reasoning

Letta V1（`letta_v1_agent`，2026）弃用了 `send_message`/heartbeat 和内联的 `Thought:` token，改用 native reasoning。Responses API（OpenAI）和带扩展思考的 Messages API（Anthropic）在独立通道上输出推理，跨轮次传递（生产环境中跨提供商加密）。控制循环仍是 ReAct。思维轨迹是结构化的，而非 prompt 形状的。

### 该模式在哪里会出错

- **Block 膨胀。** 无限 `block_append` 会很快触及上限。在写出超过上限的写入之前挂一个 block 摘要器。
- **静默漂移。** sleep-time agent 重写了一个 block，主 agent 却从未察觉。给 blocks 做版本化，并在轨迹里展示 diff。
- **有毒的整合。** sleep-time agent 把攻击者可触及的内容处理进 core。Lesson 27 同样适用于 sleep-time 表面。

```figure
memory-blocks
```

## Build It

`code/main.py` 实现：

- `Block` —— id、label、value、limit、description。
- `BlockStore` —— CRUD + `near_limit(label)` 辅助函数。
- 两个脚本化 agent —— `PrimaryAgent` 提供一轮服务，`SleepTimeAgent` 在轮次之间整合。
- 一段轨迹，展示带 block 写入的三轮对话，外加一次 sleep-time 遍历：摘要一个 block 并失效一个过时事实。

运行：

```
python3 code/main.py
```

转录展示了分工：primary 轮次很快并产生原始写入；sleep 遍历做压缩和清理。

## Use It

- **Letta**（letta.com）作为参考实现。自托管或托管云。
- **Claude Agent SDK skills** 作为 block 形状的知识——skill 是一个具名、带版本、可检索的指令块，agent 按需加载。
- **自定义构建** 用于想要控制存储后端、并打算之后迁移的团队。使用 Letta API 契约。

## Ship It

`outputs/skill-memory-blocks.md` 为任意运行时生成一个 Letta 形状的 block 系统，带 sleep-time 钩子，并接入安全规则和引用接线。

## 练习

1. 添加一个 `block_summarize` 工具：当 `near_limit` 返回 true 时，用模型生成的摘要替换 block 值。哪个触发阈值能同时最小化摘要调用次数和 block 溢出？
2. 在 archival 上实现 sleep-time 去重：token 重叠 >90% 的两条记录合并为一条。只在 sleep 遍历中做，绝不在关键路径上做。
3. 给 blocks 做版本化。每次写入记录旧值和 diff。暴露 `block_history(label)`，让运维能调试「agent 为什么会忘记 X」。
4. 把 sleep-time agents 当作不可信的写入者。当它们触及 Persona 或 Safety block 时，提交前要求第二个 agent 审查。
5. 移植示例到 Letta API（`letta_v1_agent`）。block schema 有什么变化，native reasoning 如何改变轨迹形状？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Memory block | 「可编辑的 prompt section」 | Core 记忆中带类型、持久、可由 LLM 编辑的片段 |
| Human block | 「用户记忆」 | 关于用户的事实，固定在 core 里 |
| Persona block | 「agent 身份」 | 自我概念、语气、约束，固定在 core 里 |
| Sleep-time compute | 「异步记忆工作」 | 在关键路径之外做整合的第二个 agent |
| Core / Recall / Archival | 「层」 | 三层记忆划分：始终可见 / 对话 / 外部 |
| Block limit | 「上限」 | 每个 block 的字符上限；强制摘要 |
| Native reasoning | 「思考通道」 | 提供商级的推理输出，而非 prompt 级的 `Thought:` |
| Learned context | 「sleep 输出」 | sleep-time agent 写进共享 blocks 的事实 |

## 延伸阅读

- [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) —— block 模式
- [Letta, Sleep-time Compute blog](https://www.letta.com/blog/sleep-time-compute) —— 异步整合
- [Letta, Rearchitecting the Agent Loop](https://www.letta.com/blog/letta-v1-agent) —— native reasoning 重写
- [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) —— 起源