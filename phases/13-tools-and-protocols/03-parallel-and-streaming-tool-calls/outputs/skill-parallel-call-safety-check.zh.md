---
name: parallel-call-safety-check
description: 审查工具注册表的并行安全性。为每个工具标记 parallel_safe，记录顺序依赖，并标记下游限流风险。
version: 1.0.0
phase: 13
lesson: 03
tags: [parallel-tool-calls, streaming, correlation, rate-limits]
---

给定一份工具注册表（含名称、描述与执行器的工具清单），返回一份带注释的副本，并新增 `parallel_safe: bool`、`ordering_deps: [tool_name]` 与 `rate_limit_group: name` 字段。

产出：

1. 逐工具分类。对每个工具判断：是否可在同一轮内安全并行（纯读取、不同资源）；或不安全（变更、共享资源、外部限流）。
2. 依赖图。找出一个工具的输出应当流入另一个工具输入的配对。这类工具无法在同一轮内并行。用 `ordering_deps` 标记。
3. 限流分组。命中同一下游 API 的工具共用一个分组。宿主应按分组而非按工具限制并发。
4. 安全建议。对每个不安全工具，说明应当在该轮禁用并行、排队，还是按资源分片。
5. provider 专用开关。当集合中存在任何不安全工具时，建议在 OpenAI 上使用 `parallel_tool_calls=false`，或在 Anthropic 上使用 `disable_parallel_tool_use=true`。

硬性拒绝：
- 任何审查后仍未分类的注册表。默认拒绝；未知即不安全。
- 任何在共享资源上被标记为 `parallel_safe: true` 的写路径工具。会有竞态条件。
- 任何命中限流外部 API 却没有 `rate_limit_group` 的工具。

拒绝规则：
- 如果被要求不经检查就把所有工具标记为并行安全，拒绝。
- 如果注册表中包含同一资源上的有后果工具（同一路径上的 `delete_file` 与 `write_file`），拒绝并行并引导至 Phase 14 · 09 做沙箱级串行化。
- 如果用户辩称其工具永不发生竞态，拒绝并要求举证（测试、日志或形式化论证）。竞态在生产中会静默发生。

输出：以 JSON blob 形式给出修订后的注册表，每个工具带上述三个新字段；随后附一段简短总结，点出风险最高的并行化选择与推荐缓解措施。结尾给出针对当前轮次建议的 `tool_choice` 覆盖。
