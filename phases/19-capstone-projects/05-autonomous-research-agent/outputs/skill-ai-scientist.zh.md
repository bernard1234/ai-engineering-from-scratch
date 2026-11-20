---
name: ai-scientist
description: 构建一个自主研究 agent，运行实验树搜索、用视觉批判写出 LaTeX 论文，并通过 sandbox 逃逸红队测试。
version: 1.0.0
phase: 19
lesson: 05
tags: [capstone, autonomous-agent, ai-scientist, sakana, langgraph, sandbox, research]
---

给定一个种子想法、一个窄领域和一个 $30 的算力预算，构建一个 agent，运行实验树搜索、写出一篇可评审的 LaTeX 论文，并产出一个可复现性包。

构建计划：

1. 文献梳理：Semantic Scholar Graph API + OpenAlex；把摘要缓存进 FAISS；生成 1 页的领域摘要。
2. 树搜索：在实验节点上实现 best-first 扩展，`expand(node) -> children`（每个子节点改一项配置），`score(node) = novelty*0.4 + quality*0.5 + budget*0.1`。
3. 逐节点 sandbox：每个实验运行 `docker run --network=none --memory=8g --cpus=2 --pids-limit=256 --read-only` 或等价的 E2B 配置；确定性种子；强制资源上限。
4. Plan-execute-verify：verify 步骤检查 loss 是否收敛、baseline 是否跑过、消融是否隔离了论断。
5. 写作器：生成 LaTeX，编译成 PDF，把 PDF 送回 Claude Opus 4.7 视觉模式，就版式与论断-证据对齐做批判，最多迭代 3 次。
6. 评审团：五个评审（Opus 4.7、GPT-5.4、Gemini 3 Pro、DeepSeek R1、Qwen3-Max）按 NeurIPS 评分表（novelty、rigor、clarity、reproducibility、impact）打分；均值 < 4.0 则退回写作器。
7. 红队：集成对抗任务（fork bomb、文件系统逃逸、LLM 编写的网络调用）。确认全部被拦截。产出 `red_team.md`。
8. 可复现性包：paper.pdf + review.md + 树搜索 trace JSON + 种子 + W&B 运行链接 + sandbox 配置 + 一行重跑命令。

评估评分表：

| 权重 | 标准 | 衡量方式 |
|:-:|---|---|
| 25 | 论文质量 | 就同一内容种子的已发表 workshop 论文做盲评评分表评审 |
| 20 | 实验严谨性 | baseline、种子、消融；每个论断都由结果表中的某个单元格支撑 |
| 20 | 成本与算力纪律 | 强制每篇论文 $30 上限，Langfuse 追踪 |
| 20 | 安全性 | sandbox 红队通过；网络策略与 kill-switch 已验证，并记录尝试 |
| 15 | 可复现性 | 一键重跑用相同种子复现该论文 |

硬性驳回：

- 在 sandbox 之外运行实验。本 capstone 的全部论点是执行必须被隔离。
- 写作步骤不重新读取编译后的 PDF（视觉批判是承重的）。
- 没有 baseline、种子或消融章节的论文。
- 成本预算只作为事后警告而非硬上限来执行。

拒绝规则：

- 拒绝在评审均值低于 4.0/5 时发表论文，除非有明确的人工覆盖。
- 拒绝在需要从 sandbox 内部访问网络的种子想法上运行。改为挂载一个独立的只读数据集卷。
- 拒绝重跑红队尚未执行并记录在案的论文。

产出：一个仓库，包含树搜索引擎、sandbox 策略、写作/评审循环、三次带可复现性包的示例运行、一份红队报告、一个成本账本 csv，以及一份说明你复现了 Sakana v2 哪些失败模式、缓解如何奏效的总结。
