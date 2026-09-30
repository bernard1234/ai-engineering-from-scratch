---
name: injection-defense
description: 为任何智能体运行时构建一个 PVE（Prompt-Validator-Executor）层，包含来源标签化的内容、injection 标记扫描，以及 allowlist 导航。
version: 1.0.0
phase: 14
lesson: 27
tags: [security, prompt-injection, pve, greshake, source-tag]
---

给定一个带工具访问和检索能力的智能体，产出注入防御层。

产出：

1. 每段内容带一个来源标签：`user_message`、`tool_output`、`retrieved_web`、`retrieved_memory`、`retrieved_file`。让标签在消息历史中传播。
2. `Validator.assess(tool_call, contents)`——拒绝带 injection 形态参数或检索内容的工具调用；只有当来源标签与声明的信任级别匹配时才允许。
3. 导航的 allowlist / blocklist：智能体可以接触的 URL、域名、文件路径。
4. 记忆写入 guardrail：拒绝看起来像指令的写入。
5. 内容捕获纪律（第 23 课）：把检索到的内容存到外部；span 携带引用 ID，而非正文。
6. 测试套件：把五种 Greshake 利用类别作为 red-team 用例。

硬性拒绝：

- 没有来源标签的工具使用面。没有来源信息就无法区分权限层级。
- 只在最终输出上运行的验证器。迟到的验证毫无意义——模型早已行动。
- 「相信我，system prompt 会处理它。」system-prompt 卫生不是一项控制。

拒绝规则：

- 如果智能体有任何不带来源标签的检索能力，拒绝交付。检索到的内容是最典型的注入载体。
- 如果敏感工具（发消息、执行 shell、在 / 写文件）没有 human-in-the-loop 确认，拒绝。
- 如果记忆写入没有防护，拒绝。持久化记忆投毒会在下次会话再次毒化。

输出：`validator.py`、`source_tag.py`、`allowlist.py`、`memory_guard.py`、`red_team.py`、`README.md`，说明六层控制栈、残余风险以及持续的复核节奏。结尾附「下一步读什么」，指向第 21 课（computer use safety）和第 23 课（通过 OTel 做内容捕获）。