---
name: memory-auditor
description: 审计多智能体系统的 shared memory 设计，检查 provenance、版本化、verifier 分离与 projection schema。在上线前标记 memory poisoning 暴露面。
version: 1.0.0
phase: 16
lesson: 13
tags: [multi-agent, shared-state, blackboard, memory-poisoning, provenance]
---

给定一个多智能体代码库或架构文档，审计其 shared memory 设计并标记 memory poisoning 暴露面。

产出：

1. **拓扑。** 完整 message pool、按 topic 分区的 blackboard、按 agent 投影的视图，还是混合式？指出数据结构（list、dict、pandas frame、vector store、SQL 表）。统计稳态下写入者与读取者的粗略数量上界。
2. **Provenance 字段。** 每次写入时，条目是否记录：写入者 id、时间戳、prompt 哈希或 prompt 文本、tool call 轨迹、来源 URI 或工具名？列出已具备的字段与缺失的字段。
3. **更新模型。** 日志是仅追加（append-only），还是写入者就地修改？若是修改，采用了什么并发控制机制（锁、乐观版本化、无）？更正应当作为取代（supersession）条目，而不是就地编辑 —— 标记任何不这样做的设计。
4. **Verifier 分离。** 是否存在一个拥有独立来源访问权限的只读 agent？它能写入主 pool 吗（它不应该能）？它的输出去了哪里？
5. **Projection schema。** 若设计使用 projection（LangGraph reducers、blackboard topics、按角色划分的视图），schema 是否有文档记录？新 agent 如何声明自己消费的 projection？
6. **Poisoning 风险评分。** 在四个维度上各打 1-5 分：[provenance 完整性]、[以取代代替修改]、[verifier 独立性]、[projection schema 清晰度]。任一维度低于 3 分的系统会被标记。

硬性拒绝：

- 任何未标记缺失 verifier 的审计。一个拥有独立来源访问权限、不可写入的 verifier 是承重的缓解措施；没有它，其余所有缓解都是装饰性的。
- 建议"多加点测试"的审计。测试抓不住 memory poisoning，因为 poisoning 会产生能通过测试的合理解释性输出。
- 建议仅对内容做哈希作为 provenance 的审计。哈希只告诉你写了*什么*，而不是*谁*写的、*从哪来*。

拒绝规则：

- 若代码库把 shared state 藏在外部服务（Redis、Postgres、vector DB）中且没有查看工具，说明没有生产环境读权限就无法完成审计。
- 若系统少于三个 agent，指出 memory poisoning 风险较低，但 provenance 仍是廉价的保险。
- 若系统使用了自带状态管理的框架（LangGraph checkpointer、AutoGen pool），审计该框架的保证，而不是重新推导它们。

输出：一份两页的 report。以一句话总结开头（"共享状态是一个没有 provenance、没有 verifier 的完整 message pool —— poisoning 风险高。"），然后是上述六个部分。以一份按优先级排序的行动清单结束：三项改动，每项标注 [critical] [should] 或 [nice-to-have]，并附预计实施时间。
