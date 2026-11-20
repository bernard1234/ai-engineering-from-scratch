# 浏览器 agent 与长程 Web 任务

> ChatGPT agent（2025 年 7 月）将 Operator 与 deep research 合并为一个浏览器/终端 agent，并把 BrowseComp 的 SOTA 推到 68.9%。OpenAI 于 2025 年 8 月 31 日关停 Operator——这是产品层的整合。Anthropic 收购 Vercept 后，把 Claude Sonnet 在 OSWorld 上的成绩从不足 15% 提升到 72.5%。WebArena-Verified（ServiceNow，ICLR 2026）修正了原始 WebArena 中 11.3 个百分点的假阴性率，并发布了包含 258 个任务的 Hard 子集。这些数字是真实的。攻击面同样真实：OpenAI 的 preparedness 负责人在公开场合表示，针对浏览器 agent 的间接 prompt injection“不是一种可以被完全修补的 bug”。2025–2026 年间有记录的攻破案例包括：Tainted Memories（Atlas CSRF）、HashJack（Cato Networks），以及 Perplexity Comet 中的一键劫持。

**Type:** Learn
**Languages:** Python（stdlib，间接 prompt-injection 攻击面模型）
**Prerequisites:** 第 15 阶段，第 10 课（Permission modes）、第 15 阶段，第 01 课（Long-horizon agents）
**Time:** ~45 分钟

## 问题场景

浏览器 agent 是一种长程 agent：它读取不可信内容，并执行会产生后果的动作。agent 访问的每一个页面，都是用户没有写过的输入。每个页面上的每个表单，都是潜在的命令通道。2025–2026 年的攻击样本集表明这并非假设：Tainted Memories 让攻击者通过精心构造的页面，把恶意指令绑定到 agent 的记忆上；HashJack 把命令藏在 agent 访问的 URL 片段里；Perplexity Comet 的劫持只需一次点击即可命中。

防御方面的图景并不轻松。OpenAI 的 preparedness 负责人把大家心照不宣的话挑明了：间接 prompt injection“不是一种可以被完全修补的 bug”。原因在于，这种攻击生存在 agent 的“读取与行动”边界上，而这个边界在架构上是模糊的——模型读到的每一个 token，原则上都可能被当作一条指令。

本课会点明攻击面，梳理 benchmark 版图（BrowseComp、OSWorld、WebArena-Verified），并建模一个最小的间接 prompt injection 场景，让你能够在第 14 课和第 18 课中推理真正的防御手段。

## 核心概念

### 2026 年格局：每个系统一段话

**ChatGPT agent（OpenAI）。** 2025 年 7 月发布。把 Operator（浏览）与 Deep Research（多小时研究）合二为一。2025 年 8 月 31 日关停了独立的 Operator。BrowseComp 上达到 SOTA 68.9%；在 OSWorld 和 WebArena-Verified 上也有很强的成绩。

**Claude Sonnet + Vercept（Anthropic）。** Anthropic 收购 Vercept 后专注电脑使用能力。把 Claude Sonnet 在 OSWorld 上的成绩从 <15% 提升到 72.5%。Claude Computer Use 以工具 API 的形式提供。

**Gemini 3 Pro with Browser Use（DeepMind）。** Browser Use 集成提供电脑使用控制；FSF v3（2026 年 4 月，第 20 课）专门追踪 ML 研发领域的自主性。

**WebArena-Verified（ServiceNow，ICLR 2026）。** 修正了一个有充分记录的问题：原始 WebArena 存在约 11.3% 的假阴性率（实际已解决的任务被判为失败）。Verified 版本用人工整理的成功标准重新评分，并新增了一个 258 任务的 Hard 子集（ICLR 2026 论文，openreview.net/forum?id=94tlGxmqkN）。

### BrowseComp、OSWorld 与 WebArena 对比

| Benchmark | 衡量内容 | 时间跨度 |
|---|---|---|
| BrowseComp | 在时间压力下于开放网络上查找特定事实 | 分钟级 |
| OSWorld | agent 操作完整桌面（鼠标、键盘、shell） | 数十分钟 |
| WebArena-Verified | 在模拟站点中完成事务性 Web 任务 | 分钟级 |
| Hard 子集 | 涉及多页面状态转换的 WebArena-Verified 任务 | 数十分钟 |

维度不同。高 BrowseComp 分数说明 agent 能找到事实；它并不说明 agent 能订机票。OSWorld 分数更接近“它能不能在我的桌面上干活”。WebArena-Verified 更接近“它能不能跑完一个流程”。任何生产决策都需要与任务分布相匹配的 benchmark。

### 攻击面：逐项点名

1. **间接 prompt injection。** 不可信的页面内容里含有指令。agent 读到它们。agent 执行它们。公开案例：2024 年 Kai Greshake 等人、2025 年 Tainted Memories 论文、2026 年 HashJack（Cato Networks）。
2. **URL 片段 / 查询串注入。** 被抓取 URL 的 `#fragment` 或查询串里含有命令。它们从不可见地渲染；但仍在 agent 的 context 内。
3. **记忆绑定攻击。** 页面指示 agent 写入一条持久记忆（第 12 课涉及持久状态）。下一次会话中，这条记忆无需可见的触发即可放出 payload。
4. **针对已认证会话的 CSRF 式攻击。** Tainted Memories 这一类：agent 在某处已登录；攻击者的页面发出状态变更请求，agent 带着用户的 cookie 去执行。
5. **一键劫持。** 一个视觉上无害的按钮搭载了 agent 会跟随的 payload。Comet 这一类。
6. **agent 宿主表面的内容安全策略漏洞。** 渲染层和工具层本身就可以是攻击向量；浏览器套浏览器 agent 的栈面很宽。

### 为什么“无法完全修补”

这种攻击与 agent 的能力同构。agent 必须读取不可信内容才能完成工作。agent 读到的任何内容都可能含有指令。agent 跟随的任何指令都可能与用户实际的请求不一致。防御手段（信任边界、分类器、工具白名单、对有后果动作的 HITL）提高攻击成本、缩小其影响范围。它们并没有消除这一整类问题。

这与 Lob 定理（第 08 课）是同一个推理模式：agent 无法证明下一个 token 是安全的；它只能搭起一个系统，让不安全的 token 更容易被检测出来。

### 真正能落地的防御姿态

- **读 / 写边界。** 读取永远不产生后果。写入（提交表单、发布内容、调用带副作用的工具）在发起内容来自信任边界之外时，需要重新获得人工批准。
- **按任务配置工具白名单。** agent 可以浏览；除非该工具为当前任务显式启用，否则它不能发起电汇。第 13 课涉及预算。
- **会话隔离。** 浏览器 agent 会话只使用受限范围的凭证运行。不接入生产认证，不使用个人邮箱。留存每个 HTTP 请求的日志以供审计。
- **内容清洗器。** 抓取到的 HTML 在拼接进模型 context 之前，先剥离已知的恶意模式。（它降低简单攻击的成功率；但挡不住复杂的 payload。）
- **对有后果动作启用 HITL。** 即 propose-then-commit 模式（第 15 课）。
- **在记忆上放置 canary token。** 如果某条记忆被触发，用户会看到（第 14 课）。

```figure
injection-boundary
```

## Use It

`code/main.py` 针对三个合成页面，建模了一次微型的浏览器 agent 运行。一个页面是良性的，一个在可见文本里含有一段直接的 prompt injection，一个带有 URL 片段注入（不可见但在 agent 的 context 内）。脚本展示：(a) 一个天真 agent 会怎么做；(b) 读 / 写边界能拦住什么；(c) 清洗器能拦住什么；(d) 两者都拦不住什么。

## Ship It

`outputs/skill-browser-agent-trust-boundary.md` 为一次拟议的浏览器 agent 部署划定范围：它触及哪些信任区、被授权写入什么，以及首次运行前必须就位的防御。

## Exercises

1. 运行 `code/main.py`。找出哪种攻击会被清洗器拦住、但读 / 写边界拦不住，以及哪种攻击只有读 / 写边界才能拦住。

2. 扩展清洗器，使其检测出一类 HashJack 式的 URL 片段注入。测量在带有合法片段的良性 URL 上的误报率。

3. 挑选一个你了解的真实浏览器 agent 工作流（例如“订一张机票”）。列出每一次读取和每一次写入。标出哪些写入需要 HITL，并说明原因。

4. 阅读 WebArena-Verified 的 ICLR 2026 论文。找出原始 WebArena 评分不可靠的一类任务，并解释 Verified 子集如何解决它。

5. 为浏览器 agent 场景设计一个记忆 canary。你会存什么、存在哪里，以及什么会触发警报？

## Key Terms

| 术语 | 人们的说法 | 实际含义 |
|---|---|---|
| Indirect prompt injection | “页面坏文本” | agent 读取的页面中，不可信内容里含有 agent 会执行的指令 |
| Tainted Memories | “记忆攻击” | agent 把攻击者提供的指令写入持久记忆；在下一次会话触发 |
| HashJack | “URL 片段攻击” | 藏在 URL 片段 / 查询串里的 payload 位于 agent 的 context 内，但不可见地渲染 |
| One-click hijack | “坏按钮” | 一个可见的可操作元素搭载了 agent 会执行的后续 payload |
| BrowseComp | “Web 搜索 benchmark” | 在开放网络上查找特定事实；分钟级时间跨度 |
| OSWorld | “桌面 benchmark” | 完整的 OS 控制；多步 GUI 任务 |
| WebArena-Verified | “修好的 Web 任务 benchmark” | ServiceNow 重新评分的 WebArena，含 Hard 子集 |
| Read/write boundary | “副作用闸门” | 读取永不产生后果；写入在内容来自信任之外时需要重新批准 |

## Further Reading

- [OpenAI — Introducing ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/) — Operator 与 deep research 的合并；BrowseComp SOTA。
- [OpenAI — Computer-Using Agent](https://openai.com/index/computer-using-agent/) — Operator 的血统，以及最终成为 ChatGPT agent 的架构。
- [Zhou et al. — WebArena](https://webarena.dev/) — 原始 benchmark。
- [WebArena-Verified（OpenReview）](https://openreview.net/forum?id=94tlGxmqkN) — ICLR 2026 修正子集论文。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 包含针对电脑使用 agent 的攻击面讨论。
