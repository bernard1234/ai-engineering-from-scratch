# 混合记忆：Vector + Graph + KV

> 混合记忆并行运行三个存储——vector 用于语义相似度，KV 用于快速事实查找，graph 用于实体关系推理——并用一个打分层在检索时将它们融合。这是外部记忆广泛使用的生产模式；Mem0（Chhikara et al., 2025）是一个参考实现。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 07 (MemGPT), Phase 14 · 08 (Letta Blocks)
**Time:** ~75 minutes

## 学习目标

- 解释为什么单一存储（只有 vector、只有 graph、只有 KV）对 agent 记忆来说不够。
- 说出 Mem0 的三个并行存储以及各自优化什么。
- 描述 Mem0 的融合打分——relevance、importance、recency——以及为什么它是加权和而非层级。
- 用标准库实现一个玩具三存储记忆，含写入三个存储的 `add()` 和融合结果的 `search()`。

## 问题

对三类查询之一，单一存储是错的：

- **语义相似度** —— 「我们上周关于 agent 漂移讨论了什么？」Vector 胜出；KV 和 graph 抓不到。
- **事实查找** —— 「用户的电话号码是多少？」KV 胜出；vector 是浪费，graph 是杀鸡用牛刀。
- **关系推理** —— 「哪些客户共享同一个结算实体？」Graph 胜出；vector 和 KV 无法回答。

生产 agent 在一次会话里三类都会发。单一存储记忆对其中的两类总是错的。Mem0 的贡献是把三者接在单一 `add`/`search` 表面之后，用一个打分函数融合它们。

## 概念

### 三个并行存储

Mem0（arXiv:2504.19413，April 2025）在 `add(text, user_id, metadata)` 时：

1. 从文本中抽取候选事实（一个 LLM 驱动的步骤）。
2. 把每个事实写入 vector 存储（embedding）用于语义搜索。
3. 把每个事实写入以 (user_id, fact_type, entity) 为键的 KV 存储用于 O(1) 查找。
4. 把每个事实作为带类型的边写入 graph 存储（Mem0g）用于关系查询。

在 `search(query, user_id)` 时：

1. Vector 存储按 embedding 余弦返回 top-k。
2. KV 存储返回以查询推导出的 (user_id, type, entity) 为键的直接命中。
3. Graph 存储返回从查询实体可达的子图。
4. 一个打分层融合三者。

### 融合打分

```
score = w_relevance * relevance(q, record)
      + w_importance * importance(record)
      + w_recency * recency(record)
```

- **Relevance** —— vector 余弦、KV 精确匹配、graph 路径权重。
- **Importance** —— 在写入时标记或学习得到（有些事实更重要：姓名、ID、策略）。
- **Recency** —— 自上次写入或读取以来的指数衰减。

权重按产品调优。聊天 agent 用更高的 `w_recency`；合规 agent 用更高的 `w_importance`；检索 agent 用更高的 `w_relevance`。

### Mem0g 与时态推理

Mem0g 增加了一个冲突检测器。当新事实与现有边矛盾时，现有边被标记为无效但不删除。时态查询（「用户三月份在哪个城市？」）遍历在指定时间有效的子图。

这正是 Letta 失效模式所推广的合规级行为。

### 基准数字

Mem0 论文报告（2025）：

- **LoCoMo**（长对话记忆）：91.6
- **LongMemEval**（长跨度情节记忆）：93.4
- **BEAM 1M**（1M-token 记忆基准）：64.1

对比基线（全上下文 128k LLM、扁平 vector 存储、扁平 KV）全部输 10+ 分。基准本身不能单独证明选择——运营形态才能——但数字表明融合设计不是舍入误差。

### Scope 分类法

Mem0 按 scope 拆分记忆：

- **User memory** —— 跨会话持久，以 `user_id` 为键。
- **Session memory** —— 在单一线程内持久。
- **Agent memory** —— 每个 agent 实例的状态。

每次写入选择一个 scope。检索可跨 scope 查询，并带每 scope 权重。不假思索地混用 scope，就会得到「助手把 Bob 的项目告诉 Alice」这类事故。

### 该模式在哪里会出错

- **Embedding 漂移。** 在前一百次查询看着对的 vector 结果会随语料增长而退化。对使用最多的 top-N 记录定期重新 embedding。
- **KV schema 蔓延。** `(user_id, type, entity)` 看着简单，直到每个团队都加自己的 `type`。每季度审计 type 集合。
- **Graph 爆炸。** 一个吵闹的抽取器每条消息加 50 条边。给每次 `add` 调用限制 graph 写入数；丢弃低置信度边。

```figure
ae-memory-fusion
```

## Build It

`code/main.py` 用标准库实现三存储模式：

- `VectorStore` —— 用朴素的 token 重叠相似度充当 embedding 的替身。
- `KVStore` —— 以 `(user_id, fact_type, entity)` 为键的字典。
- `GraphStore` —— 带类型的边 (subject, relation, object, valid)。
- `Mem0` —— 顶层门面，含 `add()`、`search()`、融合打分的 scope-aware 检索。
- 一段多用户、多会话对话的工作轨迹。

运行：

```
python3 code/main.py
```

输出展示三条独立的召回路径以及融合后的 top-k。翻转 `main()` 顶部的打分权重，观察排名的变化。

## Use It

- **Mem0（Apache 2.0）** —— 生产就绪。用 Postgres + Qdrant + Neo4j 自托管，或使用托管云。
- **Letta** —— 三层 core/recall/archival；自带 vector 和 graph 后端。
- **Zep** —— 带时态 KG 和事实抽取的商业替代。
- **自定义构建** —— 当你需要精确控制抽取器（合规）或融合权重（recency 占主导的语音 agent）时。

## Ship It

`outputs/skill-hybrid-memory.md` 生成一个三存储记忆脚手架，接入融合打分器、scope 分类法和时态失效。

## 练习

1. 把玩具 vector 相似度换成真实的 embedding 模型（sentence-transformers、Ollama、OpenAI embeddings）。在一段合成的长对话上测量 recall@10。排名在 1000 次写入后会漂移吗？
2. 添加时态查询：`search(query, as_of=timestamp)`。只返回在指定时间或之前有效的记录。哪个存储需要最多改动？
3. 实现冲突检测器：如果新事实与某条 graph 边矛盾，失效旧边并记录两者。在「user lives in Berlin」→「user lives in Lisbon」上测试。
4. 把融合打分器扩展到包含 `user_feedback` 维度（对检索到的记录点赞）。如何防止刷分（agent 只返回它已经点过赞的记录）？
5. 阅读 Mem0 文档（`docs.mem0.ai`）。把玩具移植到 `mem0` 客户端调用。在同一 20 条测试查询上对比检索质量。

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Hybrid memory | 「Vector 加 graph 加 KV」 | 三个存储并行写入，检索时融合 |
| Fact extraction | 「记忆摄入」 | 把文本拆成 (entity, relation, fact) 元组的 LLM 步骤 |
| Fusion scoring | 「相关性排序」 | relevance、importance、recency 的加权和 |
| Scope | 「记忆命名空间」 | user / session / agent——决定谁看到什么 |
| Mem0g | 「记忆图谱」 | 带时态有效性的类型化边，用于关系查询 |
| Temporal invalidation | 「软删除」 | 把矛盾的边标记为无效；绝不删除 |
| Embedding drift | 「检索腐烂」 | Vector 质量随语料增长而退化；定期重新 embedding |

## 延伸阅读

- [Chhikara et al., Mem0 (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413) —— 原论文
- [Mem0 docs](https://docs.mem0.ai/platform/overview) —— 生产 API、SDK、托管云
- [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) —— 虚拟上下文的前身
- [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) —— 三层姊妹设计