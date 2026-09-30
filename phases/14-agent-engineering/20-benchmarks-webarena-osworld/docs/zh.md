# 基准测试：WebArena 与 OSWorld

> WebArena 在四个自托管应用上测试网页 agent 能力。OSWorld 在 Ubuntu、Windows、macOS 上测试桌面 agent 能力。在发布时（2023–2024），两者都显示出顶尖 agent 与人类之间的巨大差距。差距正在缩小；失败模式没有改变。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 19 (SWE-bench, GAIA)
**Time:** ~60 minutes

## 学习目标

- 描述 WebArena 的四个自托管应用，以及为什么基于执行的评测很重要。
- 解释为什么 OSWorld 使用真实操作系统截图而非无障碍 API。
- 说出 OSWorld 的两个主要失败模式：GUI grounding 与操作知识。
- 总结 OSWorld-G 和 OSWorld-Human 在基础基准之上增加了什么。

## 问题

通用 agent 能调用工具。它们能否驱动浏览器跨越 20 次点击完成一次购物结账？它们能否只用键盘和鼠标配置一台 Linux 机器？这些正是 WebArena 和 OSWorld 回答的问题。

## 概念

### WebArena（Zhou 等人，ICLR 2024）

- 跨四个自托管网页应用的 812 个长时程任务：一个购物网站、一个论坛、一个类似 GitLab 的开发工具、一个商业 CMS。
- 外加实用工具：地图、计算器、便签。
- 评测基于执行，通过 gym API——订单是否已下单、issue 是否已关闭、CMS 页面是否已更新？
- 发布时：最佳 GPT-4 agent 成功率为 14.41%，人类为 78.24%。

自托管的框架设定很重要——因为目标应用被固定且可复现，基准测试不会抖动。

### 扩展

- **VisualWebArena** —— 视觉 grounding 的任务，成功取决于对图像的解释（截图作为一等观察）。
- **TheAgentCompany**（2024 年 12 月）—— 增加终端 + 编码；更像真实的远程工作环境。

### OSWorld（Xie 等人，NeurIPS 2024）

- 跨 Ubuntu、Windows、macOS 的 369 个真实计算机任务。
- 对真实应用的自由形式键盘与鼠标控制。
- 1920×1080 截图作为观察。
- 发布时：最佳模型 12.24%，人类 72.36%。

### 主要失败模式

1. **GUI grounding。** 像素 → 元素映射。模型难以在 1920×1080 中可靠地定位 UI 元素。
2. **操作知识。** 哪个菜单有这项设置、哪个键盘快捷键、哪个偏好面板。这是人类经年累月积累的知识长尾。

### 后续工作

- **OSWorld-G** —— 564 样本的 grounding 套件 + Jedi 训练集。把 grounding 与规划解耦，以便你能分开测量。
- **OSWorld-Human** —— 人工筛选的黄金动作轨迹。显示顶尖 agent 使用了比必要多 1.4–2.7 倍的步数（轨迹效率差距）。

### 为什么这很重要

Claude computer use、OpenAI CUA、Gemini 2.5 Computer Use（第 21 课）都基于 WebArena 和 OSWorld 塑造的工作负载进行训练。基准测试是目标；生产模型是交付的答案。

### 基准测试在哪里会出错

- **仅截图的评测。** OSWorld 由截图驱动；在 OSWorld 上评测使用 DOM 或无障碍 API 的 agent，会错失 grounding 挑战。
- **忽略轨迹长度。** 只按成功率评分，会错失 OSWorld-Human 揭示的 1.4–2.7 倍步数低效。
- **过时的自托管应用。** WebArena 的应用固定了特定版本；未重新筛选就升级会破坏可比性。

```figure
ae-agent-human-gap
```

## Build It

`code/main.py` 实现了一个玩具级网页 agent harness：

- 一个极简的「购物应用」状态机：list_items、add_to_cart、checkout。
- 3 个任务的黄金轨迹。
- 一个脚本化 agent，尝试每个任务。
- 基于执行的评测器（状态检查）和轨迹效率指标（步数 vs 黄金）。

运行它：

```
python3 code/main.py
```

输出：每个任务的成功率和轨迹效率，呼应 OSWorld-Human 的方法论。

## Use It

- **WebArena Verified** 在内部集群上自托管，用于持续评测。
- **OSWorld** 在 VM 机群中运行，用于桌面 agent。
- **Computer-use agents**（第 21 课）——Claude、OpenAI CUA、Gemini——都基于这类工作负载训练。
- **你自己的产品流程** —— 为你的前 20 个任务捕获黄金轨迹；每周用 agent 对照运行。

## Ship It

`outputs/skill-web-desktop-harness.md` 构建一个网页/桌面 agent harness，带基于执行的评测和轨迹效率指标。

## 练习

1. 用第二个应用（一个论坛）扩展玩具 harness。写 3 个任务加黄金轨迹。
2. 为每个任务增加轨迹效率报告。在你的玩具上，agent 是黄金的 1 倍、2 倍还是 3 倍？
3. 实现一个「干扰」工具——一个黄金轨迹从不使用的工具。脚本化 agent 会被诱惑吗？
4. 阅读 OSWorld-G。你如何在自己的 evals 中把 grounding 失败与规划失败分开？
5. 阅读 WebArena 的应用 README。当你升级某个固定版本的应用时，什么会坏掉？

## 关键术语

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|----------------|------------------------|
| WebArena | 「网页 agent 基准」 | 跨 4 个自托管应用的 812 个任务；gym 风格评测 |
| VisualWebArena | 「视觉版 WebArena」 | 视觉 grounding 的 WebArena；截图即观察 |
| OSWorld | 「桌面 agent 基准」 | 在真实 Ubuntu/Windows/macOS 上的 369 个任务 |
| GUI grounding | 「像素到元素映射」 | 模型在 1920x1080 中定位 UI 元素 |
| Operational knowledge | 「操作系统知识」 | 哪个菜单、哪个快捷键、哪个偏好面板 |
| OSWorld-G | 「grounding 套件」 | 564 个纯 grounding 样本 + 训练集 |
| OSWorld-Human | 「黄金轨迹」 | 人工专家动作序列，用于衡量效率 |
| Trajectory efficiency | 「步数/黄金」 | agent 步数除以人类最小步数 |

## 延伸阅读

- [Zhou 等人，WebArena（arXiv:2307.13854）](https://arxiv.org/abs/2307.13854) —— 四应用网页基准
- [Xie 等人，OSWorld（arXiv:2404.07972）](https://arxiv.org/abs/2404.07972) —— 跨操作系统桌面基准
- [Anthropic，Introducing computer use](https://www.anthropic.com/news/3-5-models-and-computer-use) —— Claude 由基准塑造的能力
- [OpenAI，Computer-Using Agent](https://openai.com/index/computer-using-agent/) —— OSWorld 和 WebArena 数字
