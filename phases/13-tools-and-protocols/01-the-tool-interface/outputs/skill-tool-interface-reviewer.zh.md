---
name: tool-interface-reviewer
description: 审查一份工具定义（名称 + 描述 + JSON Schema + 执行器概要）在交付给 LLM 之前是否符合循环要求。
version: 1.0.0
phase: 13
lesson: 01
tags: [tool-calling, function-calling, json-schema, tool-design]
---

给定一份拟定的工具定义，对照四步循环（describe、decide、execute、observe）进行审查，并在工具到达模型之前标记出破坏循环的缺陷。

产出：

1. 名称审查。名称是否为 `snake_case`、跨版本稳定且无歧义？标记与内置名称冲突、含时态（“was_”“will_”）或把参数嵌进名称的名称。
2. 描述审查。描述读起来是不是一份完整的使用说明？要求采用两句话形态：“Use when X. Do not use for Y.” 标记少于 40 个字符的描述、营销式文案，以及任何没有教会模型如何选择的内容。
3. Schema 审查。schema 是否为合法的 JSON Schema 2020-12？每个字段都有类型？`required` 列表显式给出？封闭取值集合是否使用 enum？标记本应使用 enum 的开放式字符串字段、缺失的类型，以及输入对象上未声明的 `additionalProperties`。
4. 执行器审查。给定参数时执行器是否确定性？是否以带类型的错误处理失败（而不是抛出会逃出宿主的异常）？如果它有后果（改变状态、花钱、触碰用户数据），是否被如此标记并被确认闸门拦住？
5. 分类。说明该工具是 pure 还是 consequential，并给出原因。没有闸门的有后果工具应直接拒绝。

硬性拒绝：
- 任何描述只说了它做什么、却没说何时使用的工具。模型在第二步需要这个“何时”。
- 任何含无类型字段的 schema。校验器无法履行其职责。
- 任何同时满足以下三者的工具：接受不可信输入、读取敏感数据、执行有后果的动作。这违反 Meta 的 Rule of Two。
- 任何在坏输入上抛出未处理异常的执行器。宿主不应需要对每次调用都套一层 try/except。

拒绝规则：
- 如果工具定义缺少 schema，拒绝。先转至 Phase 13 · 04。
- 如果工具是 pure，但描述写着“use sparingly”，拒绝并追问原因。pure 工具重复运行应当是廉价的。
- 如果被要求批准一个连接生产数据库、却没有只读保护的工具，拒绝并引导至 Phase 13 · 17（网关与策略）。

输出：一份单页审查，列出名称、描述、schema 与执行器方面的发现，附严重程度（block / warn / nit）以及 ship / revise / reject 的最终裁决。结尾对任何被拒绝项给出单行改写建议（若可行）。
