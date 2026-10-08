---
name: virtual-memory
description: 为任意目标运行时搭建 MemGPT 形状的两层记忆系统（main context + archival store + memory tools），带正确的驱逐、引用和不可信输入处理。
version: 1.0.0
phase: 14
lesson: 07
tags: [memory, memgpt, virtual-context, archival, citations]
---

给定目标运行时（Python、Node、Rust）、模型提供商（Anthropic、OpenAI、本地）和存储后端（内存、SQLite、向量数据库、KV、graph），产出一个正确的 MemGPT 形状记忆系统。

产出：

1. 一个 `MainContext` 类型，含 `core` 字典（具名持久 sections）和 `messages` 列表（FIFO）。达到大小上限时自动驱逐；被驱逐的轮次仍可由 `conversation_search` 检索。
2. 一个带 insert 和 search 的 `ArchivalStore`。记录必须携带 `id`、`text`、`tags`、`session_id`、`turn_id`、`created_at`。每次写入返回存储的 id 用于引用。
3. 五个匹配 MemGPT 表面的 memory tools：`core_memory_append`、`core_memory_replace`、`archival_memory_insert`、`archival_memory_search`、`conversation_search`。以告诉模型何时使用每个工具的 `description` 文本呈现给模型。
4. 引用契约：每次 archival 检索必须随文本返回记录 id，agent 必须在最终答案中引用它们。无引用的答案是软失败。
5. 一个整合钩子（v1 中可以是 no-op），让 Lesson 08 的 sleep-time agents 无需重新接线即可插入。暴露 `list_records_since(timestamp)` 和 `delete(id)`。

硬拒绝：

- 用全 prompt LLM 打分搜索 archival。使用合适的检索后端（BM25、向量相似度）。LLM 重排只允许在 top-k 短列表上，而非整个语料。
- 没有驱逐策略的主上下文。无界的主上下文会静默增长超出窗口。
- 把检索到的内容当作用户指令存储。所有 archival 内容都是不可信文本（Lesson 27）。作为 observation 而非 system prompt 传给模型。
- 编写一个清空所有 sections 的 `core_memory_clear` 工具。Core 承重；清空是搬起石头砸自己的脚。支持 `replace` 而非 `clear`。

拒绝规则：

- 如果用户要求「不要引用，只要答案」，在任何来源归属重要的领域（医疗、法律、政策、金融）拒绝。提供折中：引用以脚注而非内联呈现。
- 如果用户要求「把检索到的内容不加过滤地全部写回 archival」，拒绝并指向 Lesson 27。检索内容是攻击者可触及的；一刀切回写是记忆中毒。
- 如果运行时没有持久化层，拒绝发布一个被描述为具有「长期记忆」的 agent。降级产品描述，而非实现。

输出：每个组件一个文件（`main_context.*`、`archival_store.*`、`memory_tools.*`、`agent.*`），外加一份解释驱逐策略、引用契约以及 Lesson 08（sleep-time 整合）和 Lesson 09（Mem0 融合）插入位置的 `README.md`。结尾「what to read next」：如果 agent 需要三层或异步整合，指向 Lesson 08；如果 agent 需要 vector+KV+graph 融合，指向 Lesson 09。