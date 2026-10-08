---
name: hybrid-memory
description: 生成一个 Mem0 形状的三存储记忆系统（vector + KV + graph），带融合打分器、scope 分类法和时态失效。
version: 1.0.0
phase: 14
lesson: 09
tags: [memory, mem0, vector, graph, kv, fusion, scope]
---

给定目标运行时、vector 后端（Qdrant、pgvector、Chroma、sqlite-vec）、KV 后端（Postgres、Redis、dict）和 graph 后端（Neo4j、内存边），产出一个融合的记忆系统。

产出：

1. 三个存储类，位于 `add(text, user_id, session_id, scope, importance, tags)` 门面之后。写入时，抽取器把 `text` 分解为 records、KV 三元组和 graph 三元组。没有可选存储。
2. 一个融合打分器 `score = w_rel * relevance + w_imp * importance + w_rec * recency`。把三个权重都暴露为配置。按产品调优，而非按调用。
3. Scope 分类法：`user`、`session`、`agent`。检索必须遵守 scope。用户查询绝不能泄露另一个用户的记录。
4. 时态失效。矛盾把旧边/记录标记为无效；绝不删除。暴露 `search(query, as_of=timestamp)` 用于历史查询。
5. 一个抽取器接口。默认可以是 LLM 驱动；为测试提供确定性的 regex 回退。给每次 `add()` 限制 graph 边数以防爆炸。

硬拒绝：

- 把单一存储记忆描述为「Mem0 形状」。只有 vector、只有 KV、只有 graph 的产品没问题，但不是混合记忆。不要乱命名。
- 没有每 scope 权重或显式 `scope=` 过滤器的跨 scope 检索。Scope 泄露是合规和隐私事故。
- 矛盾时删除。失效并打时间戳。删除会掩盖 bug 并破坏审计。

拒绝规则：

- 如果用户要求「不要 importance 加权」，拒绝。在百万条记录上做扁平相关性排序，是迟早要发生的检索失败。
- 如果 graph 后端没有冲突检测器，拒绝把结果系统称为「Mem0 形状」。降级该名称。
- 如果产品涉及 PII（医疗、法律、HR），拒绝发布一个未经产品负责人审计的抽取器。

输出：每个存储一个文件，外加 `memory.py`（门面）、`config.py`（权重）、解释融合权重、scope 策略、抽取器契约和失效语义的 `README.md`。结尾「what to read next」：如果 agent 需要学习新技能，指向 Lesson 10；如果记忆操作上需要 OTel spans，指向 Lesson 23；或指向 Lesson 27 获取检索上的不可信输入处理。