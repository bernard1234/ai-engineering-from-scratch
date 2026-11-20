---
name: prompt-caching-planner
description: 设计对 cache 友好的 prompt 布局，并选择正确的 provider caching 模式。
version: 1.0.0
phase: 11
lesson: 15
tags: [llm-engineering, caching, cost]
---

给定一个 prompt（system + tools + few-shot + retrieval + history + user）以及使用画像（每小时请求数、所需 TTL、provider），输出：

1. 布局。重排后的各 section，并标出唯一的 cache breakpoint；说明哪些 section 稳定、哪些易变。
2. Provider 模式。Anthropic cache_control、OpenAI 自动缓存，或 Gemini CachedContent。依据 TTL 与复用模式给出理由。
3. 盈亏平衡点。TTL 内预期的每写读取次数；用数学计算对比无 cache 的净成本。
4. 验证方案。CI 断言：第二个完全相同的请求上 cache_read_input_tokens > 0；dashboard 按 cached 与 uncached token 拆分。
5. 失败模式。列出在此设置下 cache 最可能 miss 的三个原因（动态时间戳、tool 顺序变化、近似重复文本），以及你会如何逐一防范。

拒绝交付在 breakpoint 之上放置动态字段的 cache 方案。在复用次数不足以让 2x 写入溢价回本时，拒绝启用 1h TTL。
