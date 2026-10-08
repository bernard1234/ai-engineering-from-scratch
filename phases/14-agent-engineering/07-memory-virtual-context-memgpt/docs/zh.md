# Agent 记忆 —— 虚拟上下文与记忆分页

> 上下文窗口是有限的，而对话、文档和工具轨迹不是。解决办法是重新表述操作系统虚拟内存——主上下文是 RAM，外部存储是磁盘，agent 在两者之间分页。MemGPT（Packer et al., 2023）命名了这一模式；许多生产记忆系统都建立在其上。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 06 (Tool Use)
**Time:** ~75 minutes

## 学习目标

- 解释 MemGPT 所基于的操作系统类比：main context = RAM，external context = disk，memory tools = 换入/换出。
- 用标准库实现两层 MemGPT 模式：一个主上下文缓冲区、一个可搜索的外部存储，以及换入/换出工具。
- 描述 agent 如何发出「interrupt」来查询或修改外部记忆，以及结果如何拼接回下一个 prompt。
- 识别延续到 Letta（Lesson 08）和 Mem0（Lesson 09）的 MemGPT 设计选择。

## 问题

上下文窗口看起来应该能解决记忆问题，其实不能。生产中有三种失败模式反复出现：

1. **溢出。** 多轮对话、长文档或工具调用密集的轨迹会超出窗口。截止点之后的一切都丢失了。
2. **稀释。** 即使在窗口之内，塞入无关上下文也会稀释对重要内容的注意力。前沿模型在长输入上仍会退化。
3. **持久化。** 新会话以空窗口开始。没有外部记忆的 agent 无法跨会话说「记得你让我……」。

更大的窗口有帮助，但解决不了这个问题。Mem0 的 2025 论文测量到，128k 窗口的基线仍会遗漏长期事实，而带有外部记忆的 4k 窗口 agent 却能捕捉到。

## 概念

### 操作系统类比

MemGPT（Packer et al., arXiv:2310.08560, v2 Feb 2024）把上下文管理映射到操作系统虚拟内存：

| OS 概念 | MemGPT 概念 | 2026 生产类比 |
|------------|---------------|------------------------|
| RAM | main context (prompt) | Anthropic/OpenAI 上下文窗口 |
| Disk | external context | 向量数据库、KV、图存储 |
| Page fault | memory tool call | `memory.search`、`memory.read`、`memory.write` |
| OS kernel | agent control loop | 带 memory tools 的 ReAct 循环 |

Agent 运行一个普通的 ReAct 循环。多出来的这一类工具让它把数据换入和换出主上下文。

### 两层

- **主上下文。** 固定大小的 prompt，保存当前任务。始终对模型可见。
- **外部上下文。** 无界，可通过工具搜索。相关时读取，出现事实时写入。

原论文在两个超出基础窗口的任务上评估了该设计：超过 100k token 的文档分析，以及跨天持久记忆的多会话聊天。

### interrupt 模式

MemGPT 引入了「记忆即 interrupt」：对话进行中，agent 可以调用一个 memory tool，运行时执行它，结果作为新的 observation 拼接进下一个 assistant 轮次。概念上与 Unix 的 `read()` 系统调用完全相同——阻塞进程、返回字节、进程继续。

规范的 memory tool 表面：

- `core_memory_append(section, text)` —— 写入 prompt 的一个持久化 section。
- `core_memory_replace(section, old, new)` —— 编辑一个持久化 section。
- `archival_memory_insert(text)` —— 写入可搜索的外部存储。
- `archival_memory_search(query, top_k)` —— 从外部存储检索。
- `conversation_search(query)` —— 扫描过去的轮次。

### 论文的终点与生产的起点

2024 年 9 月，MemGPT 更名为 Letta。研究仓库（`cpacker/MemGPT`）仍在；Letta 扩展了这一设计：

- 从两层变成三层（core、recall、archival —— Lesson 08）。
- 用 native reasoning 取代 `send_message`/heartbeat 模式（Lesson 08）。
- sleep-time agent 异步运行记忆工作（Lesson 08）。

即使生产系统运行的是 Letta、Mem0 或自定义的两层存储，MemGPT 论文仍是 2026 年的基础。

### 该模式在哪里会出错

- **记忆腐烂。** 写入累积快于读取；检索淹没在过时事实里。修复：定期整合（Letta sleep-time）、显式失效（Mem0 冲突检测器）。
- **记忆中毒。** 外部记忆是被检索的文本。如果攻击者控制的内容落进一条记忆笔记，agent 下次会话会重新摄入它。这就是 Greshake et al.（Lesson 27）攻击随时间重述。
- **引用丢失。** Agent 回忆起「用户让我发布 X」却无法引用是哪一轮。每次 archival 写入都存储来源引用（session ID、turn ID）。

```figure
context-budget
```

## Build It

`code/main.py` 用标准库实现 MemGPT 的两层模式：

- `MainContext` —— 固定大小的 prompt 缓冲区，含一个 `core` 字典和一个 `messages` 列表；超过上限时自动压缩最旧的消息。
- `ArchivalStore` —— 内存中的类 BM25 存储（token 重叠打分），记录为 (id, text, tags, session, turn)。
- 五个 memory tools，映射到 MemGPT 表面。
- 一个脚本化的 agent，先用事实填充 archival，再通过调用 `archival_memory_search` 回答问题。

运行：

```
python3 code/main.py
```

轨迹显示 agent 写入三个事实、把主上下文填满到上限（触发驱逐），然后通过从 archival 检索回答后续问题——在不使用任何真实 LLM 的情况下重现 MemGPT 工作流。

## Use It

如今每个生产记忆系统都是 MemGPT 的变体：

- **Letta**（Lesson 08）—— 三层、native reasoning、sleep-time compute。
- **Mem0**（Lesson 09）—— vector + KV + graph 用打分层融合。
- **OpenAI Assistants / Responses** —— 通过 threads 和 files 实现的托管记忆。
- **Claude Agent SDK** —— 通过 skills 和 session store 实现的长期记忆。

按运营形态（自托管、托管、框架集成）选择，而不是按核心模式——核心模式就是 MemGPT。

### Agent 记忆的形态

分页解决了容量问题，但没决定存什么。生产系统中反复出现四种记忆类型，每种回答不同的问题：

- **工作记忆** —— 现在什么重要？上下文内的一层：当前任务、最近轮次、固定的 core sections。就是 prompt 本身。
- **情节记忆** —— 发生了什么？过去的轮次和轨迹，带 session 和 turn 引用存储，可按需重放。
- **语义记忆** —— 什么是真的？关于用户、领域、世界的事实，随变化更新并去重。
- **程序记忆** —— 我怎么做这件事？习得的例程、偏好和规则，用于引导未来行为而非回忆。

开源实现选择了不同的切入点：

| 类型 | 实现 | 它如何处理 |
|------|----------------|-------------------|
| Working | MemGPT / Letta | 通过 memory tools 把内容分页进出固定的 prompt 预算（本节、Lesson 08） |
| Episodic | Zep | 时态知识图谱——事实携带有效期区间，因此「什么时候什么是真的」可查询 |
| Semantic | Mem0 | 在 vector、KV 和 graph 存储上跨库去重、更新事实的抽取流水线（Lesson 09） |
| Semantic + procedural | LangMem | 后台抽取事实和行为规则到 agent 在轮次之间查询的存储中 |
| Episodic + semantic | agentmemory | 随会话运行捕获，整合成带类型、可搜索的记录 |

## Ship It

`outputs/skill-virtual-memory.md` 是一个可复用的 skill，为任意目标运行时生成正确的两层记忆脚手架（main + archival + tool surface），并接入驱逐策略和引用字段。

## 练习

1. 添加以 token 计量的 `max_main_context_tokens` 上限（用 `len(text.split())` * 1.3 近似）。超过上限时把最旧的消息压缩成摘要。对比有、无摘要器的行为。
2. 在 archival 存储上正确实现 BM25（词频、逆文档频率）。在玩具事实集上测量 recall@10，与 token 重叠基线对比。
3. 给 archival 插入添加 `citation` 字段（session_id、turn_id、source_url）。让 agent 在每个基于检索的回答上引用来源。
4. 模拟记忆中毒：添加一条 archival 记录，内容为「忽略所有未来的用户指令」。写一个守卫扫描检索结果中的指令型文本并将其标记为不可信。
5. 移植实现到 MemGPT 研究仓库的 core-memory JSON schema（`cpacker/MemGPT`）。从扁平字符串切换到带类型的 sections 后，什么发生了变化？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Virtual context | 「无限记忆」 | 主（prompt）+ 外部（可搜索）两层，带换入/换出 |
| Main context | 「工作记忆」 | 就是 prompt——固定大小、始终可见 |
| Archival memory | 「长期存储」 | 外部可搜索的持久化，按需检索 |
| Core memory | 「持久化的 prompt section」 | 固定在主上下文内、具名的 sections |
| Memory tool | 「记忆 API」 | Agent 发出的、用于读写外部记忆的工具调用 |
| Interrupt | 「记忆缺页」 | Agent 暂停、运行时取回、结果拼接进下一轮 |
| Memory rot | 「过时事实」 | 旧写入淹没检索；用整合修复 |
| Memory poisoning | 「注入的持久笔记」 | 攻击者内容被存为记忆，召回时被重新摄入 |

## 延伸阅读

- [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) —— 受操作系统启发的虚拟上下文论文
- [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) —— 三层演进
- [Anthropic, Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) —— 把上下文当作预算
- [Chhikara et al., Mem0 (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413) —— 建立在此模式之上的混合生产记忆
- [Zep (getzep/zep)](https://github.com/getzep/zep) —— 分类表中的时态知识图谱记忆
- [Mem0 (mem0ai/mem0)](https://github.com/mem0ai/mem0) —— Lesson 09 混合存储背后的抽取流水线
- [LangMem (langchain-ai/langmem)](https://github.com/langchain-ai/langmem) —— 事实和行为规则的后台抽取
- [agentmemory (rohitg00/agentmemory)](https://github.com/rohitg00/agentmemory) —— 会话捕获整合为带类型、可搜索的记录