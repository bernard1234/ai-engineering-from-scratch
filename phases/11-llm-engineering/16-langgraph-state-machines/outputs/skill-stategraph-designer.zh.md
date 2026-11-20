---
name: stategraph-designer
description: 把一个 agent 任务转成带命名 node、类型化 state、reducer、checkpointer 与人工中断的 LangGraph StateGraph。
version: 1.0.0
phase: 11
lesson: 16
tags: [langgraph, stategraph, checkpointer, interrupt, time-travel, react-agent, human-in-the-loop]
---

给定 agent 任务（面向用户的目标、可用 tool、预期轮数、副作用及其安全爆炸半径、持久性要求、目标延迟预算），输出：

1. Node 清单。为每个独立步骤命名：LLM 思考节点、每个 tool 执行节点、每个人工复核步骤、任何 summarizer 或 critic、任何 retriever。若某节点涉及多于一个关注点，就否掉该设计并拆分它。
2. State schema。TypedDict（或 Pydantic）字段，每个 list 都要配 reducer。消息日志上始终使用 Annotated[list, add_messages]。把任何任务专属的 list（计划、预算计数器、检索文档列表）从 messages 里提出来，这样并行更新时 reducer 才能保持正确。
3. Edge 映射。下一步确定的用静态 edge。只有在模型选择下一步的地方，才用带命名 router 函数的条件 edge。若 graph 的 router 函数依赖一次尚未在先前 node 中发出的全新 LLM 调用，则否掉该 graph。
4. Interrupt 位置。对每个带不可逆副作用的 node（写入、删除、支付、有成本的外部 API 调用）使用 interrupt_before。当输出校验在独立进程中运行时，在模型 node 上使用 interrupt_after。对有副作用的 node 一律拒绝 interrupt_after；到那时副作用已经发生了。
5. Checkpointer。MemorySaver 仅用于测试。任何必须扛过重启的环境，都要从 PostgresSaver、SQLiteSaver、RedisSaver 中选一个。确认 thread_id 策略（按用户、按 session、按对话）与 checkpoint TTL。

拒绝交付没有 checkpointer 的 LangGraph。没有 checkpointer 就没有 resume、没有 time-travel、没有 human-in-the-loop 重放。拒绝交付没有 add_messages 的 messages 字段；第二次写入会静默覆盖第一次，一半对话就此消失。拒绝所有 transition 都是被 planner LLM 路由的条件 edge 的 graph；那只是多绕几步的 AutoGen，且每轮都在烧 token。

示例输入："基于 Anthropic Claude 的退款处理 agent，有三个 tool（lookup_order、issue_refund、send_email），任何超过 100 美元的退款前必须暂停等待人工，服务器重启后必须能恢复，p95 延迟预算 8 秒。"

示例输出：
- Nodes：agent（LLM 调用）、lookup_tool、refund_tool、email_tool、human_review。
- State：messages 用 add_messages，order_context（覆盖写）、refund_amount（覆盖写）、reviewer_decision（覆盖写）。
- Edges：agent 到 should_continue router，分支为 lookup_tool、refund_tool、email_tool、human_review、END。tool node 回到 agent。
- Interrupts：当 refund_amount > 100 时在 refund_tool 上设置 interrupt_before。lookup_tool 与 email_tool 不设 interrupt。
- Checkpointer：PostgresSaver，thread_id 为 "user:{user_id}:case:{case_id}"，TTL 30 天。
