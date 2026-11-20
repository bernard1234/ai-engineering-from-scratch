# Red-Team Tooling — Garak、Llama Guard、PyRIT

> 三款生产工具构成了 2026 年的 red team 技术栈。Llama Guard（Meta）——一个在 14 个 MLCommons 风险类别上微调的 Llama-3.1-8B 分类器；2025 年的 Llama Guard 4 是一个 12B 原生多模态分类器，从 Llama 4 Scout 剪枝而来。Garak（NVIDIA）——开源 LLM 漏洞扫描器，带针对幻觉、数据泄露、prompt injection、毒性以及 jailbreak 的静态、动态与自适应 probe。PyRIT（Microsoft）——多轮 red team 行动，带 Crescendo、TAP 以及用于深度利用的自定义 converter 链。Llama Guard 3 记载于 Meta 的 “Llama 3 Herd of Models”（arXiv:2407.21783）；Llama Guard 3-1B-INT4 见于 arXiv:2411.17713；Garak 的 probe 架构见 github.com/NVIDIA/garak。这些工具是 2026 年 red team 研究（第 12-15 课）与部署（第 17 课起）之间的生产接口。

**Type:** Build
**Languages:** Python (stdlib, 工具架构模拟器与 Llama Guard 风格分类器 mock)
**Prerequisites:** 第 18 阶段，第 12 至 15 课（jailbreaks and IPI）
**Time:** ~75 分钟

## Learning Objectives

- 描述 Llama Guard 3/4 在安全栈中的位置：输入分类器、输出分类器，还是两者兼有。
- 说出 14 个 MLCommons 风险类别，并指出其中一个不那么直观的（Code Interpreter Abuse）。
- 描述 Garak 的 probe 架构：probes、detectors、harnesses。
- 描述 PyRIT 的多轮行动结构，以及它如何与 Garak probes 组合。

## 问题场景

第 12-15 课呈现了攻击面。生产部署需要可重复、可扩展的评测。2026 年有三款工具占据主导：Llama Guard（防御分类器）、Garak（扫描器）、PyRIT（行动编排器）。它们各自瞄准 red team 生命周期的不同层。

## 核心概念

### Llama Guard（Meta）

Llama Guard 3 是一个在 MLCommons AILuminate 14 个类别上做输入/输出分类微调的 Llama-3.1-8B 模型：
- 暴力犯罪、非暴力犯罪、性相关、CSAM、诽谤
- 专业建议、隐私、IP、无差别武器、仇恨
- 自杀/自残、色情内容、选举、代码解释器滥用

支持 8 种语言。用法：放在 LLM 之前（输入审核）、LLM 之后（输出审核），或两者都用。两种用法产生不同的训练分布——Llama Guard 3 以单个模型同时承担两者。

Llama Guard 3-1B-INT4（arXiv:2411.17713，440MB，移动 CPU 上约 30 tokens/s）是量化边缘版本。

Llama Guard 4（2025 年 4 月）是 12B、原生多模态，从 Llama 4 Scout 剪枝而来。它用一个同时接受文本 + 图像的分类器，取代了 8B 文本版与 11B 视觉版两个前代模型。

### Garak（NVIDIA）

开源漏洞扫描器。架构：
- **Probes。** 针对幻觉、数据泄露、prompt injection、毒性、jailbreak 的攻击生成器。静态（固定 prompt）、动态（生成的 prompt）、自适应（回应目标输出）。
- **Detectors。** 对照预期失败模式（toxic、leaked、jailbroken）对输出打分。
- **Harnesses。** 管理 probe-detector 配对，运行行动，生成报告。

TrustyAI 把 Garak 与 Llama-Stack shields（Prompt-Guard-86M 输入分类器、Llama-Guard-3-8B 输出分类器）集成，实现端到端的受保护目标评测。基于档位的评分（TBSA）取代二元的通过/失败——在同一个 probe 上，模型可以在严重度档位 3 通过、在档位 5 失败。

### PyRIT（Microsoft）

Python Risk Identification Toolkit。多轮 red team 行动。围绕以下构造：
- **Converters。** 变换种子 prompt——改写、编码、翻译、角色扮演。
- **Orchestrators。** 运行行动：Crescendo（升级）、TAP（分叉）、RedTeaming（自定义循环）。
- **Scoring。** LLM-as-judge 或 classifier-as-judge。

PyRIT 是 Garak 更重的表亲。Garak 跑成千上万的单轮 probe；PyRIT 跑旨在击破特定失败模式的深度多轮行动。

### 技术栈

把 Llama Guard 放在模型的两侧。每晚跑 Garak 做回归。发布前用 PyRIT 跑行动。这是 2026 年大多数生产部署的默认配置。

### 评测陷阱

- **Judge 身份。** 三款工具都可以用 LLM judge；judge 校准会左右报告的 ASR（第 12 课）。要连同工具一起指明 judge。
- **Probe 陈旧。** 随着模型针对 Garak probes 打了补丁，probes 会过时。自适应 probes（PAIR 形态）过时得比静态 probes 慢。
- **Llama Guard 在良性内容上的 FPR。** 早期 Llama Guard 版本对政治与 LGBTQ+ 内容过度标记；Llama Guard 3/4 的校准有所改善，但并未按部署逐一校准。

### 本课在第 18 阶段中的位置

第 12-15 课是攻击族别。第 16 课是生产工具。第 17 课（WMDP）是双用途能力评测。第 18 课是把这些工具包进策略结构的前沿安全框架。

```figure
al-guard-stack
```

## Use It

`code/main.py` 构建一个玩具 Llama Guard 风格分类器（覆盖 14 个类别的关键词 + 语义特征）、一个玩具 Garak harness（probe-detector 循环）以及一条 PyRIT 风格的多轮 converter 链。你可以对 mock 目标运行这三款工具，观察不同的覆盖特征。

## Ship It

本课产出 `outputs/skill-red-team-stack.md`。给定一份部署描述，它指明三款工具中哪些适用、各自要配置什么，以及要执行怎样的回归节奏。

## Exercises

1. 运行 `code/main.py`。比较 Llama Guard 风格分类器在单轮与多轮攻击上的检出率。

2. 实现一个新的 Garak probe：base64 编码的有害请求。测量 Llama Guard 风格分类器对它的检出。

3. 给 PyRIT 风格的 converter 链扩展一个“先翻成法语，再改写”的 converter。重新测量攻击成功率。

4. 阅读 Llama Guard 3 的风险类别清单。找出两个在训练数据上很可能对合法开发者内容产生高误报率的类别。

5. 比较 Garak 与 PyRIT 的设计原则。论证各自作为正确工具适用的部署场景。

## Key Terms

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Llama Guard | “the classifier” | 在 14 个风险类别上微调的 Llama-3.1-8B/4-12B 安全分类器 |
| Garak | “the scanner” | NVIDIA 开源漏洞扫描器；probes、detectors、harnesses |
| PyRIT | “the campaign tool” | Microsoft 多轮 red team 编排器；converters、orchestrators、scoring |
| Prompt-Guard | “the small classifier” | Meta 的 86M prompt injection 分类器，与 Llama Guard 搭配 |
| TBSA | “tier-based scoring” | Garak 的基于档位评分，取代二元结果 |
| Converter chain | “paraphrase + encode + ...” | PyRIT 用于构建多步攻击的组合原语 |
| MLCommons hazard categories | “the 14 taxonomies” | Llama Guard 瞄准的行业标准分类体系 |

## Further Reading

- [Meta — Llama Guard 3（见 Llama 3 Herd 论文，arXiv:2407.21783）](https://arxiv.org/abs/2407.21783) — 8B 分类器
- [Meta — Llama Guard 3-1B-INT4（arXiv:2411.17713）](https://arxiv.org/abs/2411.17713) — 量化移动端分类器
- [NVIDIA Garak — GitHub](https://github.com/NVIDIA/garak) — 扫描器仓库与文档
- [Microsoft PyRIT — GitHub](https://github.com/Azure/PyRIT) — 行动工具包
