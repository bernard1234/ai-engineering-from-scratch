# 多模态 Agent 与 Computer-Use（毕业项目）

> 2026 年的前沿产品是一个多模态 Agent：它读取截图、点击按钮、在 Web UI 中导航、填写表单，并端到端完成工作流。SeeClick 和 CogAgent（2024）证明了 GUI grounding 这一基础能力。Ferret-UI 补上了移动端。ChartAgent 引入了面向图表的可视工具调用。VisualWebArena 和 AgentVista（2026）是前沿追逐的基准——即便是 Gemini 3 Pro 和 Claude Opus 4.7，在 AgentVista 的困难任务上也只有约 30% 的得分。本毕业项目把 Phase 12 的所有线索汇聚起来：感知（高分辨率 VLM）、推理（带工具调用的 LLM）、grounding（坐标输出）、长时程记忆与评估。

**Type:** Capstone
**Languages:** Python（stdlib，action schema + agent loop 骨架）
**Prerequisites:** Phase 12 · 05 (LLaVA)、Phase 12 · 09 (Qwen-VL JSON)、Phase 14（Agent Engineering）
**Time:** ~240 分钟

## Learning Objectives

- 设计一个多模态 agent loop：感知 → 推理 → 行动 → 观察 → 循环。
- 构建一个 GUI grounding 输出 schema（点击坐标、输入文本、滚动、拖拽），让 VLM 能以 JSON 形式输出。
- 比较纯截图 Agent、accessibility tree Agent 与混合 Agent。
- 在一个小型 VisualWebArena 切片上搭建多模态 Agent 基准评估。

## 问题场景

一个订票网站的工作流："帮我找一趟 4 月 15 日飞东京的航班，靠过道座位，价格低于 $800，把它订下来。"

一个多模态 Agent 需要：

1. 截取浏览器屏幕。
2. 把截图 + URL + 目标解析成一个计划。
3. 输出结构化动作：点击（在 x,y 处）、输入 "Tokyo"（在元素 E 处）、向下滚动、选择（单选按钮）。
4. 把动作应用到浏览器。
5. 观察新状态（下一张截图）。
6. 重复直到任务完成。

每一步都是一次多模态 VLM 调用。VLM 的输出必须是可解析的 JSON。错误会跨步骤累积，因此恢复机制至关重要。

## 核心概念

### GUI grounding——基础能力

GUI grounding 指的是：给定一张截图和一条自然语言指令，输出要点击的 (x, y) 坐标（或其他动作）。

SeeClick（arXiv:2401.10935）是第一个规模化开放的结果：在合成 + 真实 GUI 数据上微调 VLM，把坐标作为纯文本 token 输出。可行。

CogAgent（arXiv:2312.08914）为密集 UI 增加了 1120x1120 高分辨率编码。得分：Web 导航上约 84%。

Ferret-UI（arXiv:2404.05719）聚焦移动端 UI，与 iOS accessibility 数据集成。

输出格式通常是 JSON：

```json
{"action": "click", "x": 384, "y": 220, "element_desc": "Search button"}
```

`element_desc` 有助于恢复：如果坐标在不同截图之间发生漂移，这个语义提示可以让系统重新 grounding。

### Action schema

典型的 action schema 有 6-10 种动作类型：

- `click`：(x, y)
- `type`：(text, x?, y?)
- `scroll`：(direction, amount)
- `drag`：(x0, y0, x1, y1)
- `select`：(option_index)
- `hover`：(x, y)
- `navigate`：(url)
- `wait`：(ms)
- `done`：(success, explanation)

Agent 每步输出一个动作。浏览器封装层执行它并返回新状态。

### 纯截图 vs accessibility tree

两种输入模式：

- 纯截图：完整图像，没有结构化信息。最通用；适用于任何应用。
- Accessibility tree：结构化的 DOM / iOS accessibility 信息。对 grounding 可靠得多；在树可用的地方都能用。
- 混合：两者兼用，以树作为原子动作的可靠 grounding 依据，以截图提供语义上下文。

生产级 Agent 在可能时使用混合模式。浏览器自动化（Selenium + accessibility）总能拿到树；桌面应用有时可以。

### 长时程记忆

一个 20 步的工作流会产生 20 张截图。VLM 的上下文很快就会被填满。三种压缩策略：

- 摘要链（Summary-chain）：每 5 步之后，总结已经发生的事情，丢弃旧截图。
- 跳帧（Skip-frame）：保留第一张、最后一张以及每第 3 张截图。
- 工具记录日志（Tool-recorded log）：执行动作，保留一份已完成事项的文本日志；不再回看旧截图。

Claude 的 computer-use API 采用日志模式。更简单，也更可靠。

### 可视工具调用

ChartAgent（arXiv:2510.04514）为图表理解引入了可视工具调用：裁剪、缩放、OCR、调用外部检测。Agent 可以输出"裁剪到区域 (100, 200, 300, 400) 然后调用 OCR"作为一次工具调用。工具返回文本；VLM 继续推理。

这一模式可以推广：set-of-mark prompting、区域标注、外部检测工具都符合同一套"输出工具调用、接收结构化响应"的 schema。

### 2026 年的基准

- ScreenSpot-Pro。在约 1k 张 Web 截图上做 GUI grounding。开源 SOTA Qwen2.5-VL-72B 约 85%。前沿约 90%。
- VisualWebArena。端到端 Web 任务（购物、论坛、分类广告）。开源 SOTA 约 20%。Gemini 3 Pro 约 27%。
- AgentVista（arXiv:2602.23166）。2026 年最难的基准。覆盖 12 个领域的真实工作流。前沿模型得分 27-40%；开源模型 10-20%。
- WebArena / WebShop。较老的基准；已被前沿模型刷满。

### 为什么仍然很难

Agent 性能瓶颈：

1. 细粒度视觉 grounding。在移动端分辨率下"点击那个小 X"经常失败。
2. 长时程规划。执行 10 个动作之后，Agent 会偏离目标。
3. 错误恢复。当一次点击失败（点错按钮）时，检测并恢复很少出现在训练数据中。
4. 跨页面上下文。在标签页之间跳转或处理长表单会丢失状态。

研究方向：记忆架构、显式重新规划、多模态验证（用截图匹配来确认动作成功）。

### 毕业项目的 Build It 部分

毕业项目任务：构建一个 computer-use Agent，它能够：

1. 读取订票网站模拟页面的 HTML + 截图。
2. 规划多步序列：搜索 → 选择 → 填写表单 → 提交。
3. 输出符合 action schema 的 JSON 动作。
4. 在一个固定的 10 任务切片上评估。

本课提供的脚手架代码很容易扩展成真实浏览器。

```figure
mm-agent-loop
```

## Use It

`code/main.py` 是毕业项目脚手架：

- Action schema 的 JSON 定义（10 种动作）。
- 以 dict 表示的模拟浏览器状态。
- Agent loop 骨架：接收状态、输出动作、应用、循环。
- 10 任务迷你基准（合成页面），用于衡量端到端成功率。
- 动作失败时的错误恢复钩子。

## Ship It

本课产出 `outputs/skill-multimodal-agent-designer.md`。给定一个 computer-use 产品（领域、动作集合、评估目标），设计完整的 agent loop、记忆策略、grounding 模式以及预期基准得分。

## Exercises

1. 给 action schema 扩展一个 `screenshot_region` 工具（裁剪 + 缩放）。哪些任务会受益？

2. 阅读 AgentVista（arXiv:2602.23166）。描述最难的任务类别，以及前沿模型为什么仍然失败。

3. 长时程记忆压缩：设计一个摘要链，最多保留 4 张截图活跃，任意数量的截图进入日志。

4. 构建一个错误恢复钩子：动作失败时（找不到按钮），Agent 接下来做什么？

5. 在 10 个 Web 任务上比较纯截图的 Claude 4.7 与混合截图 + accessibility-tree 的 Qwen2.5-VL。各自在哪些任务上胜出？

## Key Terms

| 术语 | 常见说法 | 实际含义 |
|------|----------|----------|
| GUI grounding | "Click coordinates" | 模型在截图上为指令目标输出 (x,y) 坐标 |
| Action schema | "Tool definitions" | 对合法动作（click、type、scroll、drag）的 JSON 描述 |
| Accessibility tree | "Structured DOM" | 来自浏览器/iOS API 的机器可读 UI 层次结构 |
| Hybrid agent | "Screenshot + tree" | 同时使用图像与结构化信息；比单独使用任一种都更可靠 |
| Visual tool use | "Zoom/crop/detect" | Agent 在规划中途调用外部视觉工具（OCR、检测） |
| Summary-chain | "Memory compression" | 周期性文本摘要替代冗长的截图历史 |
| VisualWebArena | "E2E web bench" | 2024 年用于端到端 Web 任务的基准 |
| AgentVista | "2026 hard bench" | 覆盖 12 个领域的真实工作流；即便是 Gemini 3 Pro 也只有约 30% |

## Further Reading

- [Cheng et al. — SeeClick (arXiv:2401.10935)](https://arxiv.org/abs/2401.10935)
- [Hong et al. — CogAgent (arXiv:2312.08914)](https://arxiv.org/abs/2312.08914)
- [You et al. — Ferret-UI (arXiv:2404.05719)](https://arxiv.org/abs/2404.05719)
- [ChartAgent (arXiv:2510.04514)](https://arxiv.org/abs/2510.04514)
- [Koh et al. — VisualWebArena (arXiv:2401.13649)](https://arxiv.org/abs/2401.13649)
- [AgentVista (arXiv:2602.23166)](https://arxiv.org/abs/2602.23166)
