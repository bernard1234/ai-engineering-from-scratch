# 技能库与终身学习（Voyager）

> Voyager（Wang 等人，TMLR 2024）把可执行代码当作技能。技能有名字、可检索、可组合，并由环境反馈精炼。这是 Claude Agent SDK skills、skillkit 以及 2026 年 skill-library 模式的参考架构。

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 07 (MemGPT), Phase 14 · 08 (Letta Blocks)
**Time:** ~75 minutes

## 学习目标

- 说出 Voyager 的三个组件——自动课程（automatic curriculum）、技能库（skill library）、迭代提示（iterative prompting）——以及各自的作用。
- 解释为什么 Voyager 把动作空间设为代码，而不是原始命令。
- 用标准库实现一个带注册、检索、组合和失败驱动精炼的技能库。
- 把 Voyager 的模式映射到 2026 年的 Claude Agent SDK skills 和 skillkit 生态。

## 问题

每一轮会话都从头重建所有能力的智能体，会犯三个错误：

1. **浪费 token。** 每个任务都重新唤起同样的推理。
2. **丢失进展。** 在会话 A 里学到的一次修正，不会迁移到会话 B。
3. **在长时程组合上失败。** 复杂任务需要能力层级；一次性 prompt 无法表达它们。

Voyager 的回答：把每一个可复用能力当作一段有名字的代码，存在库里，按相似度检索，与其他技能组合，并由执行反馈精炼。

## 概念

### 三个组件

Voyager（arXiv:2305.16291）围绕以下三点组织一个智能体：

1. **自动课程。** 一个由好奇心驱动的提议器（proposer），根据智能体当前的技能集和环境状态挑选下一个任务。探索是自下而上的。
2. **技能库。** 每个技能都是可执行代码。任务成功时新增技能。技能按「查询—描述」相似度检索。
3. **迭代提示机制。** 失败时，智能体会收到执行错误、环境反馈和自验证输出，然后精炼这个技能。

Minecraft 评估（Wang 等人，2024）：相比基线，独特物品多 3.3 倍，石质工具快 8.5 倍，铁质工具快 6.4 倍，地图穿越距离长 2.3 倍。这些数字是 Minecraft 特有的，但模式可以迁移。

### 动作空间 = 代码

大多数智能体输出原始命令。Voyager 输出 JavaScript 函数。一个技能是：

```
async function craftIronPickaxe(bot) {
  await mineIron(bot, 3);
  await mineStick(bot, 2);
  await placeCraftingTable(bot);
  await craft(bot, 'iron_pickaxe');
}
```

由子技能组合而成。按描述和 embedding 存储。检索时得到的是一段程序，而不是一段 prompt。

这就是 2026 年的 Claude Agent SDK skill：一段有名字、可检索的代码加指令，智能体按需加载。

### 技能检索

新任务「造一把钻石镐」。智能体：

1. 把任务描述做 embedding。
2. 在技能库里查询 top-k 个最相似的技能。
3. 检索 `craftIronPickaxe`、`mineDiamond`、`placeCraftingTable` 等。
4. 用检索到的原语加上新逻辑，组合出新技能。

这就是 MCP resources（第 13 阶段）和 Agent SDK skills 实现的模式：在一个知识/代码表面上做检索，范围限定在当前任务。

### 迭代精炼

Voyager 的反馈循环：

1. 智能体写一个技能。
2. 技能对着环境运行。
3. 返回三种信号之一：`success`、`error`（带堆栈跟踪）、`self-verification failure`。
4. 智能体用该信号作为上下文重写技能。
5. 循环直到成功或达到最大轮数。

这就是 Self-Refine（第 05 课）应用于带环境锚定验证的代码生成。CRITIC（第 05 课）是同样的模式，只是用外部工具作为验证器。

### 课程与探索

Voyager 的课程模块会根据智能体已经有什么、还没做什么来提议任务，比如「在湖边建一个庇护所」。提议器用环境状态 + 技能清单来挑选一个刚好高于当前能力的任务——这正是探索的甜点区。

对生产智能体来说，这就转化为一个「还缺什么」算子：给定当前技能库和一个领域，我们还有哪些技能没覆盖到？团队通常以课程评审的形式手工实现这一点。

### 这个模式在哪里会出问题

- **技能库腐化。** 同一个技能加了 10 次，描述略有不同。在写入时加去重；检索只返回一个。
- **组合技能漂移。** 父技能依赖的一个子技能被精炼过了。给技能做版本化；一个钉在 v1 的父技能不会自动拿到 v3。
- **检索质量。** 当库增长到几百个之后，基于技能描述的向量检索会退化。用标签过滤和硬约束（「只要 `category=tooling` 的技能」）来补充。

```figure
voyager-skills
```

## Build It

`code/main.py` 实现了一个标准库技能库：

- `Skill` —— name、description、code（作为字符串）、version、tags、dependencies。
- `SkillLibrary` —— register、search（token 重叠）、compose（依赖的拓扑排序）、refine（更新时递增 version）。
- 一个脚本化智能体：注册三个原始技能，组合出第四个，遇到一次失败，然后精炼。

运行它：

```
python3 code/main.py
```

trace 展示了库写入、检索、组合、一次失败的执行，以及一次 v2 精炼——Voyager 的循环从头到尾。

## Use It

- **Claude Agent SDK skills**（Anthropic）—— 2026 年的参考：每个技能有描述、代码和指令；在智能体会话期间按需加载。
- **skillkit**（npm: skillkit）—— 面向 32+ 个 AI 编码智能体的跨智能体技能管理。
- **自定义技能库** —— 领域专用（数据智能体的 SQL 技能、基础设施智能体的 Terraform 技能）。Voyager 模式可以向下缩放。
- **OpenAI Agents SDK `tools`** —— 处于低端；每个工具就是一个轻量技能。

## Ship It

`outputs/skill-skill-library.md` 针对任意目标运行时，生成一个 Voyager 形状的技能库，接好注册、检索、版本化与精炼。

## 练习

1. 给 `compose()` 加一个依赖环检测器。当技能 A 依赖 B、B 依赖 A 时会发生什么？报错还是警告？
2. 实现逐技能的版本钉死。当父技能组合子技能 `crafting@1` 时，把 `crafting` 精炼到 `crafting@2` 绝不能静默地升级父技能。
3. 把 token 重叠检索替换为 sentence-transformers 的 embedding（或一个 BM25 的标准库实现）。在一个 50 技能玩具库上测 retrieval@5。
4. 加一个「课程」智能体：给定当前库和一个领域描述，提议 5 个缺失的技能。每周调用一次。
5. 读 Anthropic 的 Claude Agent SDK skill 文档。把玩具库移植到 SDK 的 skill schema。可发现性会发生什么变化？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| Skill | 「可复用能力」 | 一段有名字的代码 + 描述，按相似度可检索 |
| Skill library | 「智能体的怎么做记忆」 | 技能的持久存储，可搜索、可组合 |
| Curriculum | 「任务提议器」 | 由当前能力缺口驱动的自下而上目标生成器 |
| Composition | 「技能 DAG」 | 技能调用技能；执行时做拓扑排序 |
| Iterative refinement | 「自校正循环」 | 环境反馈 + 错误 + 自验证折叠回下一个版本 |
| Action-space-as-code | 「程序化动作」 | 输出函数而非原始命令，以获得时间上延展的行为 |
| Dedup on write | 「技能坍缩」 | 近似重复的描述坍缩成一个规范技能 |

## 延伸阅读

- [Wang 等人，Voyager（arXiv:2305.16291）](https://arxiv.org/abs/2305.16291) —— 技能库的原论文
- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— 作为 2026 年产品化的 skills
- [Anthropic，Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) —— 实践中的 skills 与 subagents
- [Madaan 等人，Self-Refine（arXiv:2303.17651）](https://arxiv.org/abs/2303.17651) —— Voyager 底下的精炼循环