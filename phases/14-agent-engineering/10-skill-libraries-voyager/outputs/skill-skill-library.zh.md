---
name: skill-library
description: 生成一个 Voyager 形状的技能库，带注册、按相似度检索、组合执行与失败驱动精炼。
version: 1.0.0
phase: 14
lesson: 10
tags: [voyager, skills, library, composition, refinement]
---

给定一个目标运行时和一个领域，产出一个支持 Voyager 三个组件（课程钩子、可检索的技能存储、迭代精炼）的技能库。

产出：

1. `Skill` 类型，带 `name`、`description`、`code`、`version`、`tags`、`depends_on`、`history`。每次写入记录先前的代码。
2. `SkillLibrary`，带 `register(skill, dedup=True)`（新增或版本递增）、`search(query, top_k, tag_filter)`、`get(name)`、`topo_order(name)`（依赖解析）、`execute(name, context)`（拓扑运行）。
3. 检索必须用 embedding 相似度或 BM25，而不是对整个库做 LLM 评分。允许在 top-k 短名单上做 LLM 重排。
4. 执行必须逐技能捕获异常，并把它们作为精炼循环可以消费的反馈浮到 trace 里。
5. 精炼钩子：在一次失败的 `execute` 之后，运行时收集（task、skill_name、error、env_state），把它交给模型，并对重写后的技能调用 `register`。版本递增；history 保留旧代码。

硬拒绝：

- 技能是散文字符串而非代码的库。技能必须可执行。散文属于 `description`。
- 没有拓扑排序的组合。没有环检测的深度优先会在技能 DAG 上崩。
- 静默的版本覆盖。每次精炼必须递增 `version` 并把旧代码推入 `history` 以供审计。

拒绝规则：

- 如果目标运行时没有技能执行沙箱，对技能会触碰生产系统的领域拒绝。上线前要求一个沙箱（第 09 课原则）。
- 如果用户要求「每次失败都自动重试、不做精炼」，拒绝。没有精炼的重试会放大 bug；它修不好 bug。
- 如果库超过约 200 个技能却用扁平检索，拒绝称之为「生产就绪」。先加标签过滤和分层命名空间。

输出：`skill.py`、`library.py`、`execute.py`、`refine.py`，以及一个解释去重规则、检索后端、精炼 prompt 和版本策略的 `README.md`。结尾加「接下来读什么」，指向第 17 课（Claude Agent SDK 集成）、第 16 课（OpenAI Agents SDK 工具翻译）或第 30 课（评估技能库质量）。